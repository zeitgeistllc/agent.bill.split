import os
import streamlit as st
import tempfile
from dotenv import load_dotenv
import json
import re
from PIL import Image
import base64
import fitz # PyMuPDF

from langchain_ollama import ChatOllama
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted
from langchain_core.messages import HumanMessage

# ==============================================================================
# 1. CORE LOGIC - We now have TWO distinct analysis pipelines.
# ==============================================================================

def get_llm(provider, ollama_model, gemini_model, api_key):
    """Initializes and returns the selected conversational language model."""
    if provider == "Ollama (Local)":
        try:
            return ChatOllama(model=ollama_model, temperature=0)
        except Exception as e:
            st.error(f"Ollama initialization failed: {e}")
            st.stop()
    elif provider == "Gemini (Google)":
        if not api_key:
            st.warning("נדרש מפתח API של Google Gemini.")
            st.stop()
        try:
            return ChatGoogleGenerativeAI(model=gemini_model, google_api_key=api_key, temperature=0)
        except Exception as e:
            st.error(f"Gemini initialization failed: {e}")
            st.stop()

def analyze_document_with_gemini(file_path: str, llm: ChatGoogleGenerativeAI) -> dict:
    """Uses Gemini 1.5 Pro's multimodal capabilities for analysis."""
    st.write(f"🕵️‍♂️ מנתח את הקובץ עם Gemini Vision: `{os.path.basename(file_path)}`...")
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    mime_type = "application/pdf" if file_path.endswith(".pdf") else f"image/{os.path.splitext(file_path)[1].lstrip('.')}"
    prompt = """
    Analyze the provided file (image or PDF) and return a structured JSON object.
    First, determine the document_type: "arnona_bill", "utility_bill", "meter_reading", or "unknown".
    Then, extract the relevant numerical values for that type: 'total_amount', 'total_consumption', 'fixed_charges', 'meter_reading'.
    Use 0 for missing values. Respond with ONLY a single, valid JSON object.
    """
    message = HumanMessage(content=[{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode()}"}}])
    response = llm.invoke([message])
    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if not json_match: raise ValueError(f"Gemini did not return valid JSON. Raw response: {response.content}")
    try: return json.loads(json_match.group(0))
    except json.JSONDecodeError: raise ValueError(f"Gemini returned malformed JSON: {json_match.group(0)}")

def analyze_document_locally_with_ollama(file_path: str, structure_llm: ChatOllama) -> dict:
    """
    A completely local pipeline. Uses Llava for OCR and another Ollama model for structuring.
    """
    st.write(f"🕵️‍♂️ מנתח את הקובץ מקומית עם Ollama: `{os.path.basename(file_path)}`...")
    extracted_text = ""
    # --- Step 1: Use Llava for OCR on the image or PDF pages ---
    vision_model = ChatOllama(model="llava", temperature=0)
    if file_path.endswith('.pdf'):
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            st.write(f"  - מעבד עמוד {i+1} עם llava...")
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as tmp:
                img.convert("RGB").save(tmp, format="jpeg")
                tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            os.remove(tmp_path)
            msg = HumanMessage(content=[{"type": "text", "text": "Extract all text from this image."}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}])
            res = vision_model.invoke([msg])
            extracted_text += res.content + "\n"
        doc.close()
    else: # It's an image
        with open(file_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode('utf-8')
        msg = HumanMessage(content=[{"type": "text", "text": "Extract all text from this image."}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}])
        res = vision_model.invoke([msg])
        extracted_text = res.content
    
    if not extracted_text.strip(): raise ValueError("Llava (vision model) failed to extract any text.")
    
    # --- Step 2: Use the main Ollama model (e.g., codellama) to structure the text ---
    st.write("🧠 מבין את הטקסט שחולץ...")
    prompt = f"""
    Analyze the text below. Determine the document_type ("arnona_bill", "utility_bill", "meter_reading", or "unknown")
    and extract the relevant values: 'total_amount', 'total_consumption', 'fixed_charges', 'meter_reading'.
    Use 0 for missing values. Respond with ONLY a single, valid JSON object.
    Text: --- {extracted_text} ---
    """
    response = structure_llm.invoke(prompt)
    json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if not json_match: raise ValueError(f"The structuring model did not return valid JSON. Raw response: {response.content}")
    try: return json.loads(json_match.group(0))
    except json.JSONDecodeError: raise ValueError(f"The structuring model returned malformed JSON: {json_match.group(0)}")

def execute_calculation(data: dict, apt1_consumption: float = None) -> str:
    """Calls the correct Python function based on the structured data."""
    doc_type = data.get("document_type")
    
    if doc_type == "arnona_bill":
        total = data.get("total_amount", 0.0)
        if total == 0: return "שגיאה: לא נמצא סכום כולל בחשבון הארנונה."
        split = total / 2
        return f"--- חלוקת ארנונה ---\nסך הכל: {total:.2f}\nדירה 1: {split:.2f}\nדירה 2: {split:.2f}"
        
    elif doc_type == "utility_bill":
        total_bill = data.get("total_amount", 0.0)
        if total_bill == 0: return "שגיאה: חסר סכום כולל בחשבון."
        
        if apt1_consumption is None:
            st.session_state.needs_apt1_consumption = True
            st.session_state.utility_data = data
            return "נמצאו נתוני החשבון. אנא ספק את הצריכה של דירה 1."

        fixed_charges = data.get("fixed_charges", 0.0)
        total_consumption = data.get("total_consumption", 0.0)
        consumption_cost = total_bill - fixed_charges
        cost_per_unit = consumption_cost / total_consumption if total_consumption > 0 else 0
        apt1_fixed = fixed_charges / 2
        apt1_consumption_cost = apt1_consumption * cost_per_unit
        apt1_total = apt1_fixed + apt1_consumption_cost
        apt2_consumption = total_consumption - apt1_consumption
        apt2_fixed = fixed_charges / 2
        apt2_consumption_cost = apt2_consumption * cost_per_unit
        apt2_total = apt2_fixed + apt2_consumption_cost
        return f"--- סיכום חשבון ---\nדירה 1 ({apt1_consumption} יח'): {apt1_total:.2f}\nדירה 2 ({apt2_consumption} יח'): {apt2_total:.2f}"

    elif doc_type == "meter_reading":
        return f"קריאת המונה שזוהתה היא: {data.get('meter_reading', 'לא ידוע')}"
    else:
        return f"לא הצלחתי לזהות את סוג המסמך '{doc_type}'."

# ==============================================================================
# 2. STREAMLIT UI - Rewritten to select the correct analysis pipeline.
# ==============================================================================

st.set_page_config(page_title="מפצל החשבונות", layout="centered")
st.markdown("<style>body, .stApp { direction: rtl; } h1, .st-caption, [data-testid='stFileUploader'] label, .st-emotion-cache-1gulkj5, [data-testid='stAlert'], [data-testid='stSidebar'] * { text-align: right; } [data-testid='stChatMessageContent'] * { text-align: right; } [data-testid='stChatInput'] textarea { direction: rtl, text-align: right; }</style>", unsafe_allow_html=True)

st.sidebar.title("הגדרות מודל")
model_provider = st.sidebar.radio("בחר ספק:", ("Ollama (Local)", "Gemini (Google)"), key="model_provider")

google_api_key = None
gemini_model_name = "gemini-1.5-pro-latest"
ollama_model_name = "codellama"

if model_provider == "Ollama (Local)":
    st.sidebar.info("ניתוח קבצים יתבצע באופן מקומי באמצעות המודלים llava ו-codellama.")
    ollama_model_name = st.sidebar.selectbox("בחר מודל לשיחה:", ("codellama", "llama3", "mistral"), key="ollama_model")
else: # Gemini
    st.sidebar.info("ניתוח קבצים יתבצע באמצעות Gemini 1.5 Pro. הבחירה למטה היא עבור שיחות כלליות.")
    load_dotenv()
    google_api_key = st.sidebar.text_input("מפתח API של Gemini:", type="password", value=os.getenv("GOOGLE_API_KEY", ""), key="gemini_key")
    gemini_model_name = st.sidebar.selectbox("בחר מודל לשיחה:", ("gemini-1.5-pro-latest", "gemini-1.5-flash-latest"), key="gemini_model")

llm = get_llm(model_provider, ollama_model_name, gemini_model_name, google_api_key)

st.title("📄🤖 מפצל החשבונות")
st.caption("העלו קבצים וכתבו לי מה לעשות.")

if "messages" not in st.session_state: st.session_state.messages = []
if "uploaded_file_paths" not in st.session_state: st.session_state.uploaded_file_paths = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

uploaded_files = st.file_uploader("העלאת קבצים:", accept_multiple_files=True, key="file_uploader")
if uploaded_files:
    temp_dir = tempfile.mkdtemp()
    st.session_state.uploaded_file_paths = []
    for f in uploaded_files:
        path = os.path.join(temp_dir, f.name)
        with open(path, "wb") as out_file: out_file.write(f.getvalue())
        st.session_state.uploaded_file_paths.append(path)
    st.info(f"הועלו {len(st.session_state.uploaded_file_paths)} קבצים.")

if prompt := st.chat_input("מה נרצה לעשות?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("...חושב ומעבד"):
            try:
                if st.session_state.uploaded_file_paths:
                    all_results = []
                    for file_path in st.session_state.uploaded_file_paths:
                        if model_provider == "Gemini (Google)":
                            if not google_api_key: st.error("נדרש מפתח API של Google Gemini."); st.stop()
                            analysis_llm = get_llm("Gemini (Google)", "", "gemini-1.5-pro-latest", google_api_key)
                            structured_data = analyze_document_with_gemini(file_path, analysis_llm)
                        else: # Ollama
                            structured_data = analyze_document_locally_with_ollama(file_path, llm)
                        
                        st.write(f"**תוצאות עבור `{os.path.basename(file_path)}`:**"); st.json(structured_data)
                        result = execute_calculation(structured_data)
                        all_results.append(result)
                    
                    final_output = "\n\n---\n\n".join(all_results)
                    st.markdown(final_output)
                    st.session_state.messages.append({"role": "assistant", "content": final_output})
                    st.session_state.uploaded_file_paths = []

                elif st.session_state.get("needs_apt1_consumption"):
                    apt1_consumption_float = float(prompt)
                    utility_data = st.session_state.utility_data
                    final_split = execute_calculation(utility_data, apt1_consumption_float)
                    st.markdown(final_split)
                    st.session_state.messages.append({"role": "assistant", "content": final_split})
                    st.session_state.needs_apt1_consumption = False
                    del st.session_state.utility_data
                
                else:
                    response = llm.invoke(prompt)
                    st.markdown(response.content)
                    st.session_state.messages.append({"role": "assistant", "content": response.content})

            except (ValueError, ResourceExhausted) as e:
                st.error(f"שגיאה: {e}")
            except Exception as e:
                st.error(f"אירעה שגיאה בלתי צפויה: {e}")

if not uploaded_files and st.session_state.get("uploaded_file_paths"):
    st.session_state.uploaded_file_paths = []
    st.rerun()


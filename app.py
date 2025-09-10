import os
import streamlit as st
import fitz  # PyMuPDF
import tempfile
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

# ==============================================================================
# 1. AGENT PROMPT TEMPLATE
# This is the agent's "brain." It's based on your specific instructions.
# ==============================================================================
AGENT_TEMPLATE = """
# תפקיד ומטרה
אתה מוגדר כעוזר אישי אוטומטי לניהול וחלוקת חשבונות ביתיים. תפקידך המרכזי הוא לחלץ נתונים מחשבונות (PDF) ומתמונות מונים (JPG), ולאחר מכן לחלק את העלויות בין שתי דירות על בסיס הנתונים שחולצו והכללים שיוגדרו.

# כללים וזרימת עבודה

1.  **הבנת המשימה:** קודם כל, הבן מה המשתמש רוצה לעשות. האם הוא רוצה לחלק חשבון? לחלץ נתונים מקובץ? עליך להבין את המטרה לפני שאתה פועל.

2.  **איסוף נתונים:**
    * **אם המשתמש העלה קבצים:** השתמש בכלי `pdf_reader_tool` עבור קבצי PDF ובכלי `meter_reader_tool` עבור תמונות. חלץ את כל הנתונים הרלוונטיים.
    * **אם חסר מידע:** לאחר ניתוח הקבצים או קריאת הבקשה, אם חסר לך מידע קריטי לחישוב (למשל, קריאת מונה קודמת, סכום קבוע בחשבון), **עצור ושאל את המשתמש ישירות**. אל תנסה לנחש.
        * דוגמה לשאלה: "ניתחתי את חשבון החשמל ולא מצאתי את סך הצריכה בקוט"ש. אנא הקלד את הנתון הזה."
        * דוגמה נוספת: "זיהיתי את קריאת המונה הנוכחית מהתמונה כ-9831.1. מה הייתה קריאת המונה הקודמת של דירה 1?"
    * **זיכרון:** השתמש ב-`get_previous_reading_tool` כדי לבדוק אם קריאת מונה קודמת כבר קיימת בזיכרון. לאחר חישוב, השתמש ב-`save_current_reading_tool` כדי לשמור את הקריאה הנוכחית לעתיד.

3.  **ביצוע חישובים:**
    * **ארנונה:** השתמש ב-`arnona_calculator_tool` לחלוקה של 50/50.
    * **מים וחשמל:** השתמש ב-`bill_calculator_tool`. עליך לספק לו את כל הפרמטרים הנדרשים: `total_bill`, `fixed_charges`, `total_consumption`, ו-`apt1_consumption`.

4.  **הצגת התוצאות:**
    * הצג את הפלט הסופי בצורה ברורה ומסודרת, כפי שהכלי מחזיר אותו.
    * ודא שהפלט כולל טבלת סיכום ברורה לכל חשבון, עם פירוט החיובים עבור 'דירה 1' ו'דירה 2', כולל חלוקה לעלויות קבועות ועלויות צריכה.
    * אם חילקת מספר חשבונות, הצג סיכום **"סה"כ לתשלום כולל"** המראה את הסכום הסופי שכל דירה חייבת לשלם.

**TOOLS:**
------
You have access to the following tools. You must use the tool names from this list: {tool_names}
Here are the detailed descriptions of the tools:
{tools}

**RESPONSE FORMAT:**
------
Use the following format for your response.

Thought: Your reasoning process in Hebrew.
Action: The name of the tool to use, from the list above.
Action Input: The input for the tool.
Observation: The result from the tool.
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now have enough information to provide the final answer to the user.
Final Answer: Your final, comprehensive response to the user, formatted in Hebrew according to the output rules.

Begin!

User's Request: {input}
Thought Log: {agent_scratchpad}
"""


# ==============================================================================
# 2. TOOLS DEFINITION
# All tools are defined here as simple functions with the @tool decorator.
# ==============================================================================

@tool
def bill_calculator_tool(total_bill: float, fixed_charges: float, total_consumption: float, apt1_consumption: float) -> str:
    """
    Calculates the bill split for water or electricity between two apartments.
    Takes the total bill amount, any fixed charges, the total consumption (e.g., in kWh or m³),
    and the consumption of Apartment 1.
    It splits fixed charges 50/50 and the rest based on consumption.
    Returns a formatted string detailing the split for each apartment.
    """
    try:
        # Input validation
        if total_bill < 0 or fixed_charges < 0 or total_consumption < 0 or apt1_consumption < 0:
            return "Error: All numerical inputs must be non-negative."
        if fixed_charges > total_bill:
            return "Error: Fixed charges cannot be greater than the total bill."
        if apt1_consumption > total_consumption:
            return "Error: Apartment 1 consumption cannot be greater than total consumption."

        # Calculations
        consumption_cost = total_bill - fixed_charges
        cost_per_unit = consumption_cost / total_consumption if total_consumption > 0 else 0

        apt1_fixed = fixed_charges / 2
        apt1_consumption_cost = apt1_consumption * cost_per_unit
        apt1_total = apt1_fixed + apt1_consumption_cost

        apt2_consumption = total_consumption - apt1_consumption
        apt2_fixed = fixed_charges / 2
        apt2_consumption_cost = apt2_consumption * cost_per_unit
        apt2_total = apt2_fixed + apt2_consumption_cost

        # Verification
        if not abs((apt1_total + apt2_total) - total_bill) < 0.01:
             return f"Error: Calculation mismatch. Apt1({apt1_total}) + Apt2({apt2_total}) != Total({total_bill})."

        # Formatting output
        result = (
            "--- סיכום חלוקת חשבון ---\n"
            f"דירה 1:\n"
            f"  - חלק בתשלומים קבועים: {apt1_fixed:.2f}\n"
            f"  - עלות צריכה ({apt1_consumption} יחידות): {apt1_consumption_cost:.2f}\n"
            f"  - סך הכל: {apt1_total:.2f}\n"
            f"דירה 2:\n"
            f"  - חלק בתשלומים קבועים: {apt2_fixed:.2f}\n"
            f"  - עלות צריכה ({apt2_consumption} יחידות): {apt2_consumption_cost:.2f}\n"
            f"  - סך הכל: {apt2_total:.2f}\n"
            f"---------------------------\n"
            f"אימות: סך החלוקה תואם לסכום החשבון."
        )
        return result

    except ZeroDivisionError:
        return "שגיאה: סך הצריכה הוא אפס, לא ניתן לחשב עלות ליחידה."
    except Exception as e:
        return f"שגיאה לא צפויה: {e}"

@tool
def arnona_calculator_tool(total_arnona: float) -> str:
    """
    Calculates a 50/50 split of the total Arnona (property tax) bill.
    Takes the total Arnona amount and returns a string detailing the split.
    """
    if total_arnona < 0:
        return "שגיאה: סכום הארנונה חייב להיות מספר חיובי."
    split_amount = total_arnona / 2
    return (
        f"--- חלוקת ארנונה ---\n"
        f"דירה 1 חייבת: {split_amount:.2f}\n"
        f"דירה 2 חייבת: {split_amount:.2f}\n"
        f"סך הכל: {total_arnona:.2f}"
    )

@tool
def pdf_reader_tool(file_path: str) -> str:
    """
    Reads all text from a PDF file. The input must be a valid file path.
    """
    try:
        doc = fitz.open(file_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return f"טקסט שחולץ מ-{file_path}:\n\n{text}" if text.strip() else f"לא נמצא טקסט בקובץ {file_path}."
    except Exception as e:
        return f"שגיאה בקריאת קובץ PDF בנתיב '{file_path}': {e}"

@tool
def meter_reader_tool(file_path: str) -> str:
    """
    Placeholder to simulate reading a meter from an image. Returns a dummy value.
    """
    return f"התמונה בנתיב '{file_path}' עובדה בהצלחה. תוצאת זיהוי תווים דמה: 9831.1"

# For memory, we will use a simple session_state variable instead of a file.
@tool
def get_previous_reading_tool(meter_type: str) -> str:
    """
    Gets the previous meter reading saved in memory.
    Input must be 'electricity' or 'water'.
    """
    key = f"previous_{meter_type}_reading"
    reading = st.session_state.get(key, "לא נמצא")
    return f"קריאת המונה הקודמת עבור {meter_type} היא: {reading}"

@tool
def save_current_reading_tool(meter_type: str, reading: float) -> str:
    """
    Saves the current meter reading to memory for next time.
    Input must be meter_type ('electricity' or 'water') and the new reading.
    """
    key = f"previous_{meter_type}_reading"
    st.session_state[key] = reading
    return f"קריאת המונה עבור {meter_type} נשמרה בהצלחה: {reading}."


# ==============================================================================
# 3. AGENT CREATION
# ==============================================================================

@st.cache_resource
def create_bill_splitter_agent():
    """
    Creates and configures the bill splitting agent executor.
    """
    load_dotenv()
    if not os.getenv("GOOGLE_API_KEY"):
        st.error("GOOGLE_API_KEY not found in .env file. Please create one.")
        st.stop()
    
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)
    
    tools = [
        bill_calculator_tool,
        arnona_calculator_tool,
        pdf_reader_tool,
        meter_reader_tool,
        get_previous_reading_tool,
        save_current_reading_tool
    ]
    
    # We now use our custom prompt template instead of the generic one from the hub
    prompt = PromptTemplate.from_template(AGENT_TEMPLATE)
    
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)


# ==============================================================================
# 4. STREAMLIT UI
# ==============================================================================

st.set_page_config(page_title="מפצל החשבונות", layout="centered")
st.title("📄🤖 מפצל החשבונות")
st.caption("אני כאן כדי לעזור בחלוקת חשבונות. העלו קבצים וכתבו לי מה לעשות.")

agent_executor = create_bill_splitter_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

uploaded_files = st.file_uploader(
    "העלאת חשבונות (PDF) או קריאות מונה (JPG/PNG)",
    type=['pdf', 'png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

file_info_string = ""
if uploaded_files:
    temp_dir = tempfile.mkdtemp()
    file_paths = [os.path.join(temp_dir, f.name) for f in uploaded_files]
    for uploaded_file, path in zip(uploaded_files, file_paths):
        with open(path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    
    file_info_string = (
        "המשתמש העלה את הקבצים הבאים. השתמש בנתיבים המלאים שלהם כדי לעבד אותם:\n"
        + "\n".join(file_paths)
    )
    st.info(f"הועלו בהצלחה: `{'`, `'.join([f.name for f in uploaded_files])}`")

if prompt := st.chat_input("מה נרצה לעשות?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    agent_input = f"{prompt}\n\n{file_info_string}"

    with st.chat_message("assistant"):
        with st.spinner("...חושב"):
            try:
                response = agent_executor.invoke({"input": agent_input})
                output = response.get("output", "נתקלתי בשגיאה.")
                st.markdown(output)
                st.session_state.messages.append({"role": "assistant", "content": output})
            except Exception as e:
                error_message = f"אירעה שגיאה: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})


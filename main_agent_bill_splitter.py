import streamlit as st
import re
import pandas as pd
import io
from PIL import Image

try:
    import fitz  # PyMuPDF
    HAVE_FITZ = True
except ImportError:
    HAVE_FITZ = False
try:
    from pdf2image import convert_from_bytes
    HAVE_PDF2IMAGE = True
except ImportError:
    HAVE_PDF2IMAGE = False
try:
    import pytesseract
    HAVE_PYTESSERACT = True
except ImportError:
    HAVE_PYTESSERACT = False

RE_TOTAL = re.compile(r'(סה"?כ(?: לתשלום)?|סכום לתשלום|סה"כ|Amount Due|Total)\D{0,10}([\d,\.]+)', flags=re.I)
RE_FIXED = re.compile(r'(חיוב קבוע|קבוע|Fixed[^:\d]*)\D{0,10}([\d,\.]+)', flags=re.I)
RE_USAGE = re.compile(r'(קוט"ש|קוטש|kwh|מ"ק|מ״ק|m3)[^\d]{0,10}([\d,\.]+)', flags=re.I)

def extract_from_pdf(pdf_bytes):
    if HAVE_FITZ:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = [p.get_text("text") for p in doc]
            text = "\n".join(pages)
            if len(text.strip()) > 10:
                return text
        except Exception as e:
            pass
    if HAVE_PDF2IMAGE and HAVE_PYTESSERACT:
        try:
            images = convert_from_bytes(pdf_bytes)
            return "\n".join([pytesseract.image_to_string(img, lang="heb+eng") for img in images])
        except Exception as e:
            pass
    return ""

def extract_from_image(img_bytes):
    if HAVE_PYTESSERACT:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        result = pytesseract.image_to_string(img, lang="eng+heb")
        matches = re.findall(r'\d+(?:\.\d+)?', result.replace(',', '.'))
        if matches:
            try:
                return float(matches[0])
            except:
                return None
        return None
    return None

def extract_bill_data(text):
    total = None
    m = RE_TOTAL.search(text)
    if m:
        try: total = float(m.group(2).replace(',', ''))
        except: total = None
    fixed = 0.0
    m = RE_FIXED.search(text)
    if m:
        try: fixed = float(m.group(2).replace(',', ''))
        except: fixed = 0.0
    usage = None
    m = RE_USAGE.search(text)
    if m:
        try: usage = float(m.group(2).replace(',', ''))
        except: usage = None
    return total, fixed, usage

def split_two_apts(total, fixed, total_usage, apt1_usage):
    apt1_fixed = round(fixed / 2, 2)
    apt2_fixed = fixed - apt1_fixed
    apt2_usage = total_usage - apt1_usage
    apt1_total = round(apt1_fixed + apt1_usage, 2)
    apt2_total = round(total - apt1_total, 2)  # difference, not direct computation
    return pd.DataFrame([
        {'דירה': 'דירה 1', 'קבוע': apt1_fixed, 'צריכה': apt1_usage, 'סה"כ': apt1_total},
        {'דירה': 'דירה 2', 'קבוע': apt2_fixed, 'צריכה': apt2_usage, 'סה"כ': apt2_total},
    ])

def split_arnona(total):
    half = round(total / 2, 2)
    return pd.DataFrame([
        {'דירה': 'דירה 1', 'קבוע': half, 'צריכה': 0.0, 'סה"כ': half},
        {'דירה': 'דירה 2', 'קבוע': half, 'צריכה': 0.0, 'סה"כ': half},
    ])

st.set_page_config(page_title="Agent Bill Splitter", layout="wide")
st.title("🤖 חשבונות דירות - מערכת אוטומטית")

# ========== Step 1: Collect current meter readings ==========
st.header("1. קריאות מונה פנימיות נוכחיות לדירה 1")
curr_meter_elec = st.number_input("קריאת מונה חשמל נוכחית (דירה 1)", min_value=0.0, step=0.1)
curr_meter_water = st.number_input("קריאת מונה מים נוכחית (דירה 1)", min_value=0.0, step=0.1)

curr_img_elec = st.file_uploader("או העלה תמונה/צילום מונה חשמל נוכחי (דירה 1)", type=["jpg", "jpeg", "png"], key="elec_img")
if curr_img_elec:
    val = extract_from_image(curr_img_elec.read())
    if val is not None:
        curr_meter_elec = val
        st.success(f"זוהתה קריאת חשמל: {val}")

curr_img_water = st.file_uploader("או העלה תמונה/צילום מונה מים נוכחי (דירה 1)", type=["jpg", "jpeg", "png"], key="water_img")
if curr_img_water:
    val = extract_from_image(curr_img_water.read())
    if val is not None:
        curr_meter_water = val
        st.success(f"זוהתה קריאת מים: {val}")

# ========== Step 2: Upload bills ==========
st.header("2. העלה 3 חשבונות: מים | חשמל | ארנונה")
uploaded_bills = st.file_uploader("חשבונות PDF / תמונה", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

# ========== Step 3: Process each bill ==========
tables, types = [], []
for file in uploaded_bills or []:
    st.subheader(f"חשבונית: {file.name}")
    text = ""
    if file.name.lower().endswith('.pdf'):
        text = extract_from_pdf(file.read())
    else:
        text = pytesseract.image_to_string(Image.open(io.BytesIO(file.read())), lang="heb+eng") if HAVE_PYTESSERACT else ""
    st.expander("טקסט מזוהה").write(text)
    total, fixed, usage = extract_bill_data(text)
    # Detect type
    lowtext = text.lower()
    if "ארנונה" in lowtext or "arnona" in lowtext:
        types.append("arnona")
        if total is None:
            total = st.number_input("סכום כולל ארנונה (נדרש)", min_value=0.0, key=file.name)
        df = split_arnona(total)
        st.write(df)
        tables.append(df)
    elif "חשמל" in lowtext or "kwh" in lowtext or 'קוט"ש' in lowtext or 'קוטש' in lowtext:
        types.append("electricity")
        prev_meter = st.number_input("הזן קריאת מונה חשמל קודמת (דירה 1) או העלה תמונה:", min_value=0.0, key=file.name+"elec_prev")
        img_meter = st.file_uploader("תמונה של מונה חשמל קודם (לא חובה)", type=["jpg", "jpeg", "png"], key=file.name+"elec_prev_img")
        if img_meter:
            meter_prev_extr = extract_from_image(img_meter.read())
            if meter_prev_extr is not None:
                prev_meter = meter_prev_extr
                st.success(f"זוהתה קריאה קודמת: {meter_prev_extr}")
        if total is None:
            total = st.number_input("סכום כולל לחשמל (נדרש)", min_value=0.0, key=file.name+"elec_total")
        if usage is None:
            usage = st.number_input("סך הצריכה (kWh) על פי החשבון הראשי", min_value=0.0, key=file.name+"usage")
        apt1_usage = round(curr_meter_elec - prev_meter, 2) if curr_meter_elec and prev_meter else usage / 2 if usage else 0
        df = split_two_apts(total, fixed, usage, apt1_usage)
        st.write(df)
        tables.append(df)
    elif "מים" in lowtext or "m3" in lowtext or 'מ"ק' in lowtext or 'מ״ק' in lowtext:
        types.append("water")
        prev_meter = st.number_input("הזן קריאת מונה מים קודמת (דירה 1) או העלה תמונה:", min_value=0.0, key=file.name+"water_prev")
        img_meter = st.file_uploader("תמונה של מונה מים קודם (לא חובה)", type=["jpg", "jpeg", "png"], key=file.name+"water_prev_img")
        if img_meter:
            meter_prev_extr = extract_from_image(img_meter.read())
            if meter_prev_extr is not None:
                prev_meter = meter_prev_extr
                st.success(f"זוהתה קריאה קודמת: {meter_prev_extr}")
        if total is None:
            total = st.number_input("סכום כולל מים (נדרש)", min_value=0.0, key=file.name+"water_total")
        if usage is None:
            usage = st.number_input("סך הצריכה (m3) על פי החשבון", min_value=0.0, key=file.name+"water_usage")
        apt1_usage = round(curr_meter_water - prev_meter, 2) if curr_meter_water and prev_meter else usage / 2 if usage else 0
        df = split_two_apts(total, fixed, usage, apt1_usage)
        st.write(df)
        tables.append(df)
    else:
        st.warning("לא זוהה סוג החשבון בודאות (מים/חשמל/ארנונה).")

# ========== Step 4: Grand Total ==========
if tables:
    st.header("סיכום כולל:")
    sum1 = sum(float(t.loc[t["דירה"] == "דירה 1", 'סה"כ'].iloc[0]) for t in tables)
    sum2 = sum(float(t.loc[t["דירה"] == "דירה 2", 'סה"כ'].iloc[0]) for t in tables)
    st.table(pd.DataFrame([
        {"דירה": "דירה 1", "סה\"כ לתשלום כולל": round(sum1, 2)},
        {"דירה": "דירה 2", "סה\"כ לתשלום כולל": round(sum2, 2)}
    ]))

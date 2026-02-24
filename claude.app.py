import streamlit as st
import pandas as pd
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
from datetime import datetime

st.set_page_config(page_title="Bill Splitter", layout="wide")

# =========================
# OCR & PDF Extraction
# =========================
class BillProcessor:
    """Process and extract data from bills and meter readings"""
    
    def __init__(self):
        self.extracted_data = {
            "electricity": {},
            "water": {},
            "tax": {},
            "elec_meter": {},
            "water_meter": {}
        }

    def extract_text_from_pdf(self, pdf_bytes):
        images = convert_from_bytes(pdf_bytes)
        full_text = ""
        for img in images:
            text = pytesseract.image_to_string(img, lang='heb+eng')
            full_text += text + "\n"
        return full_text

    def extract_meter_reading(self, text, keywords):
        # Search for numbers near keywords
        for line in text.splitlines():
            for word in keywords:
                if word in line:
                    numbers = [float(s.replace(",", ".")) for s in line.split() if s.replace(".", "").isdigit()]
                    if numbers:
                        return numbers[0]
        return 0.0

    def process_electricity(self, pdf_bytes):
        text = self.extract_text_from_pdf(pdf_bytes)
        self.extracted_data['electricity'] = {
            "total": self.extract_meter_reading(text, ['חשמל', 'קוט"ש', 'קילוואט']),
            "consumption": self.extract_meter_reading(text, ['צריכה']),
            "fixed": self.extract_meter_reading(text, ['חיובים קבועים'])
        }

    def process_water(self, pdf_bytes):
        text = self.extract_text_from_pdf(pdf_bytes)
        self.extracted_data['water'] = {
            "total": self.extract_meter_reading(text, ['מים']),
            "consumption": self.extract_meter_reading(text, ['מ"ק']),
            "fixed": self.extract_meter_reading(text, ['חיובים קבועים'])
        }

    def process_tax(self, pdf_bytes):
        text = self.extract_text_from_pdf(pdf_bytes)
        self.extracted_data['tax'] = {
            "total": self.extract_meter_reading(text, ['ארנונה'])
        }

    def process_meter_image(self, image_bytes, meter_type):
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang='heb+eng')
        value = self.extract_meter_reading(text, ['קריאה', 'מטר'])
        self.extracted_data[f"{meter_type}_meter"] = {"reading": value}


# =========================
# Main App
# =========================
def main():
    st.title("Bill Splitter Agent")

    processor = BillProcessor()

    tabs = st.tabs(["Upload Bills", "Calculation", "Extracted Data"])
    upload_tab, calc_tab, data_tab = tabs

    # -------------------------
    # Upload Tab
    # -------------------------
    with upload_tab:
        st.header("Upload your bills and meter images")

        elec_bill = st.file_uploader("Upload Electricity Bill (PDF)", type=["pdf"], key="elec_pdf")
        water_bill = st.file_uploader("Upload Water Bill (PDF)", type=["pdf"], key="water_pdf")
        tax_bill = st.file_uploader("Upload Tax Bill (PDF)", type=["pdf"], key="tax_pdf")

        elec_meter_img = st.file_uploader("Upload Electricity Meter Image", type=["png", "jpg", "jpeg"], key="elec_img")
        water_meter_img = st.file_uploader("Upload Water Meter Image", type=["png", "jpg", "jpeg"], key="water_img")

        if st.button("Process Files"):
            if elec_bill: processor.process_electricity(elec_bill.read())
            if water_bill: processor.process_water(water_bill.read())
            if tax_bill: processor.process_tax(tax_bill.read())
            if elec_meter_img: processor.process_meter_image(elec_meter_img.read(), "elec")
            if water_meter_img: processor.process_meter_image(water_meter_img.read(), "water")

            st.session_state['extracted_data'] = processor.extracted_data
            st.success("Files processed successfully!")

    # -------------------------
    # Calculation Tab
    # -------------------------
    with calc_tab:
        st.header("Calculate Charges")
        data = st.session_state.get('extracted_data', {})

        if not data:
            st.info("No extracted data yet. Please process bills first.")
        else:
            elec = data.get("electricity", {})
            water = data.get("water", {})
            tax = data.get("tax", {})

            col1, col2, col3 = st.columns(3)

            with col1:
                st.subheader("Electricity")
                elec_total = st.number_input("Total (₪)", value=float(elec.get("total", 0)), key="elec_total")
                elec_cons = st.number_input("Consumption (kWh)", value=float(elec.get("consumption", 0)), key="elec_cons")
                elec_fixed = st.number_input("Fixed Charges (₪)", value=float(elec.get("fixed", 0)), key="elec_fixed")
                elec_meter = st.number_input("Meter Reading", value=float(data.get("elec_meter", {}).get("reading", 0)), key="elec_meter")

            with col2:
                st.subheader("Water")
                water_total = st.number_input("Total (₪)", value=float(water.get("total", 0)), key="water_total")
                water_cons = st.number_input("Consumption (m³)", value=float(water.get("consumption", 0)), key="water_cons")
                water_fixed = st.number_input("Fixed Charges (₪)", value=float(water.get("fixed", 0)), key="water_fixed")
                water_meter = st.number_input("Meter Reading", value=float(data.get("water_meter", {}).get("reading", 0)), key="water_meter")

            with col3:
                st.subheader("Tax")
                tax_total = st.number_input("Total (₪)", value=float(tax.get("total", 0)), key="tax_total")

            if st.button("Compute Summary"):
                total_sum = elec_total + water_total + tax_total
                st.metric("Total Amount (₪)", total_sum)

    # -------------------------
    # Extracted Data Tab
    # -------------------------
    with data_tab:
        st.header("Extracted Data Overview")
        if st.session_state.get('extracted_data'):
            st.json(st.session_state['extracted_data'])
        else:
            st.info("No data extracted yet.")

if __name__ == "__main__":
    main()

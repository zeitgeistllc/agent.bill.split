import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import pdfplumber
import re
from datetime import datetime
from typing import Dict, Tuple, Optional
import json
import os

# Configure Streamlit page
st.set_page_config(
    page_title="מחלק חשבונות דירות",
    page_icon="🏠",
    layout="wide"
)

# Initialize session state
if 'previous_readings' not in st.session_state:
    st.session_state.previous_readings = {
        'electricity': None,
        'water': None
    }

if 'calculation_history' not in st.session_state:
    st.session_state.calculation_history = []

class BillProcessor:
    """Process and extract data from bills and meter readings"""
    
    @staticmethod
    def extract_from_pdf(pdf_file) -> Dict:
        """Extract relevant data from PDF bills"""
        try:
            extracted_data = {
                'total_amount': None,
                'consumption': None,
                'fixed_charges': None,
                'billing_period': None,
                'bill_type': None
            }
            
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() or ""
                
                # Detect bill type
                if any(word in full_text for word in ['חשמל', 'קוט"ש', 'קילוואט']):
                    extracted_data['bill_type'] = 'electricity'
                elif any(word in full_text for word in ['מים', 'מ"ק', 'קוב']):
                    extracted_data['bill_type'] = 'water'
                elif any(word in full_text for word in ['ארנונה', 'עירייה', 'מועצה']):
                    extracted_data['bill_type'] = 'tax'
                
                # Extract total amount
                amount_patterns = [
                    r'סה"כ לתשלום[:\s]*([0-9,]+\.?[0-9]*)',
                    r'לתשלום[:\s]*([0-9,]+\.?[0-9]*)',
                    r'סכום כולל[:\s]*([0-9,]+\.?[0-9]*)',
                    r'סה"כ[:\s]*([0-9,]+\.?[0-9]*)'
                ]
                
                for pattern in amount_patterns:
                    match = re.search(pattern, full_text)
                    if match:
                        amount_str = match.group(1).replace(',', '')
                        extracted_data['total_amount'] = float(amount_str)
                        break
                
                # Extract consumption (for electricity and water)
                if extracted_data['bill_type'] == 'electricity':
                    consumption_pattern = r'צריכה[:\s]*([0-9,]+\.?[0-9]*)\s*קוט"ש'
                    match = re.search(consumption_pattern, full_text)
                    if match:
                        extracted_data['consumption'] = float(match.group(1).replace(',', ''))
                elif extracted_data['bill_type'] == 'water':
                    consumption_pattern = r'צריכה[:\s]*([0-9,]+\.?[0-9]*)\s*מ"ק'
                    match = re.search(consumption_pattern, full_text)
                    if match:
                        extracted_data['consumption'] = float(match.group(1).replace(',', ''))
                
                # Extract fixed charges
                fixed_patterns = [
                    r'דמי שירות[:\s]*([0-9,]+\.?[0-9]*)',
                    r'תשלום קבוע[:\s]*([0-9,]+\.?[0-9]*)',
                    r'עלות מונה[:\s]*([0-9,]+\.?[0-9]*)'
                ]
                
                fixed_total = 0
                for pattern in fixed_patterns:
                    matches = re.findall(pattern, full_text)
                    for match in matches:
                        fixed_total += float(match.replace(',', ''))
                
                if fixed_total > 0:
                    extracted_data['fixed_charges'] = fixed_total
                
            return extracted_data
            
        except Exception as e:
            st.error(f"שגיאה בקריאת PDF: {str(e)}")
            return {}
    
    @staticmethod
    def extract_meter_reading(image_file) -> Optional[float]:
        """Extract meter reading from image using OCR"""
        try:
            image = Image.open(image_file)
            
            # Use OCR to extract text
            text = pytesseract.image_to_string(image, lang='heb+eng')
            
            # Look for number patterns (meter readings)
            number_patterns = [
                r'\b([0-9]{4,6}\.?[0-9]{0,2})\b',
                r'\b([0-9]+\.[0-9]+)\b',
                r'\b([0-9]{4,})\b'
            ]
            
            for pattern in number_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    # Return the first valid number found
                    for match in matches:
                        reading = float(match)
                        if 1000 < reading < 999999:  # Reasonable meter reading range
                            return reading
            
            return None
            
        except Exception as e:
            st.error(f"שגיאה בקריאת תמונת מונה: {str(e)}")
            return None

class BillCalculator:
    """Calculate bill splits between apartments"""
    
    @staticmethod
    def calculate_split(bill_type: str, total_amount: float, 
                        consumption: Optional[float] = None,
                        fixed_charges: Optional[float] = None,
                        apt1_consumption: Optional[float] = None) -> Dict:
        """Calculate the split between apartments based on bill type"""
        
        result = {
            'apt1': {'fixed': 0, 'consumption': 0, 'total': 0},
            'apt2': {'fixed': 0, 'consumption': 0, 'total': 0},
            'total': total_amount
        }
        
        if bill_type == 'tax':
            # City tax - 50/50 split
            result['apt1']['total'] = total_amount / 2
            result['apt2']['total'] = total_amount / 2
            
        elif bill_type in ['electricity', 'water']:
            # Fixed charges - 50/50 split
            if fixed_charges:
                result['apt1']['fixed'] = fixed_charges / 2
                result['apt2']['fixed'] = fixed_charges / 2
            
            # Consumption charges
            consumption_charges = total_amount - (fixed_charges or 0)
            
            if apt1_consumption and consumption:
                # Apartment 1 pays based on its meter reading
                apt1_ratio = apt1_consumption / consumption
                result['apt1']['consumption'] = consumption_charges * apt1_ratio
                result['apt2']['consumption'] = consumption_charges * (1 - apt1_ratio)
            else:
                # If no meter reading, split 50/50
                result['apt1']['consumption'] = consumption_charges / 2
                result['apt2']['consumption'] = consumption_charges / 2
            
            # Calculate totals
            result['apt1']['total'] = result['apt1']['fixed'] + result['apt1']['consumption']
            result['apt2']['total'] = result['apt2']['fixed'] + result['apt2']['consumption']
        
        return result

def main():
    st.title("🏠 מערכת חלוקת חשבונות דירות")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ הגדרות")
        
        st.subheader("קריאות מונה קודמות")
        prev_elec = st.number_input(
            "חשמל (קוט״ש)", 
            value=st.session_state.previous_readings['electricity'] or 0.0,
            min_value=0.0,
            step=0.1
        )
        prev_water = st.number_input(
            "מים (מ״ק)", 
            value=st.session_state.previous_readings['water'] or 0.0,
            min_value=0.0,
            step=0.1
        )
        
        if st.button("שמור קריאות קודמות"):
            st.session_state.previous_readings['electricity'] = prev_elec
            st.session_state.previous_readings['water'] = prev_water
            st.success("נשמר בהצלחה!")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📄 העלאת חשבונות", "🧮 חישוב וחלוקה", "📊 היסטוריה"])
    
    with tab1:
        st.header("העלאת קבצים")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("חשבונות (PDF)")
            
            electricity_bill = st.file_uploader(
                "חשבון חשמל", 
                type=['pdf'], 
                key="elec_bill"
            )
            
            water_bill = st.file_uploader(
                "חשבון מים", 
                type=['pdf'], 
                key="water_bill"
            )
            
            tax_bill = st.file_uploader(
                "חשבון ארנונה", 
                type=['pdf'], 
                key="tax_bill"
            )
        
        with col2:
            st.subheader("תמונות מונים")
            
            elec_meter_img = st.file_uploader(
                "מונה חשמל - דירה 1", 
                type=['jpg', 'jpeg', 'png'], 
                key="elec_meter"
            )
            
            water_meter_img = st.file_uploader(
                "מונה מים - דירה 1", 
                type=['jpg', 'jpeg', 'png'], 
                key="water_meter"
            )
        
        # Process uploaded files
        if st.button("עבד קבצים", type="primary"):
            processor = BillProcessor()
            
            # Store extracted data in session state
            if 'extracted_data' not in st.session_state:
                st.session_state.extracted_data = {}
            
            with st.spinner("מעבד קבצים..."):
                # Process bills
                if electricity_bill:
                    elec_data = processor.extract_from_pdf(electricity_bill)
                    st.session_state.extracted_data['electricity'] = elec_data
                
                if water_bill:
                    water_data = processor.extract_from_pdf(water_bill)
                    st.session_state.extracted_data['water'] = water_data
                
                if tax_bill:
                    tax_data = processor.extract_from_pdf(tax_bill)
                    st.session_state.extracted_data['tax'] = tax_data
                
                # Process meter images
                if elec_meter_img:
                    reading = processor.extract_meter_reading(elec_meter_img)
                    if reading:
                        st.session_state.extracted_data['elec_meter'] = reading
                
                if water_meter_img:
                    reading = processor.extract_meter_reading(water_meter_img)
                    if reading:
                        st.session_state.extracted_data['water_meter'] = reading
            
            st.success("הקבצים עובדו בהצלחה!")
    
    with tab2:
        st.header("חישוב וחלוקה")
        
        if 'extracted_data' not in st.session_state or not st.session_state.extracted_data:
            st.warning("אנא העלה קבצים תחילה בלשונית 'העלאת חשבונות'")
        else:
            # Manual override section
            st.subheader("עריכה ידנית (אופציונלי)")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**חשמל**")
                elec_total = st.number_input(
                    "סה״כ לתשלום (₪)",
                    value=st.session_state.extracted_data.get('electricity', {}).get('total_amount', 0.0),
                    key="elec_total_input"
                )
                elec_consumption = st.number_input(
                    "צריכה כוללת (קוט״ש)",
                    value=st.session_state.extracted_data.get('electricity', {}).get('consumption', 0.0),
                    key="elec_cons_input"
                )
                elec_fixed = st.number_input(
                    "חיובים קבועים (₪)",
                    value=st.session_state.extracted_data.get('electricity', {}).get('fixed_charges', 0.0),
                    key="elec_fixed_input"
                )
                elec_apt1_reading = st.number_input(
                    "קריאת מונה דירה 1",
                    value=st.session_state.extracted_data.get('elec_meter', 0.0),
                    key="elec_apt1_input"
                )
            
            with col2:
                st.markdown("**מים**")
                water_total = st.number_input(
                    "סה״כ לתשלום (₪)",
                    value=st.session_state.extracted_data.get('water', {}).get('total_amount', 0.0),
                    key="water_total_input"
                )
                water_consumption = st.number_input(
                    "צריכה כוללת (מ״ק)",
                    value=st.session_state.extracted_data.get('water', {}).get('consumption', 0.0),
                    key="water_cons_input"
                )
                water_fixed = st.number_input(
                    "חיובים קבועים (₪)",
                    value=st.session_state.extracted_data.get('water', {}).get('fixed_charges', 0.0),
                    key="water_fixed_input"
                )
                water_apt1_reading = st.number_input(
                    "קריאת מונה דירה 1",
                    value=st.session_state.extracted_data.get('water_meter', 0.0),
                    key="water_apt1_input"
                )
            
            with col3:
                st.markdown("**ארנונה**")
                tax_total = st.number_input(
                    "סה״כ לתשלום (₪)",
                    value=st.session_state.extracted_data.get('tax', {}).get('total_amount', 0.0),
                    key="tax_total_input"
                )
            
            st.markdown("---")
            
            # Calculate button
            if st.button("חשב חלוקה", type="primary"):
                calculator = BillCalculator()
                results = {}
                
                # Calculate electricity
                if elec_total > 0:
                    apt1_cons = None
                    if elec_apt1_reading and st.session_state.previous_readings['electricity']:
                        apt1_cons = elec_apt1_reading - st.session_state.previous_readings['electricity']
                    
                    results['electricity'] = calculator.calculate_split(
                        'electricity', elec_total, elec_consumption, 
                        elec_fixed, apt1_cons
                    )
                
                # Calculate water
                if water_total > 0:
                    apt1_cons = None
                    if water_apt1_reading and st.session_state.previous_readings['water']:
                        apt1_cons = water_apt1_reading - st.session_state.previous_readings['water']
                    
                    results['water'] = calculator.calculate_split(
                        'water', water_total, water_consumption, 
                        water_fixed, apt1_cons
                    )
                
                # Calculate tax
                if tax_total > 0:
                    results['tax'] = calculator.calculate_split('tax', tax_total)
                
                # Display results
                st.markdown("### 📊 תוצאות החלוקה")
                
                # Create summary table
                summary_data = []
                
                bill_names = {
                    'electricity': 'חשמל',
                    'water': 'מים', 
                    'tax': 'ארנונה'
                }
                
                for bill_type, bill_name in bill_names.items():
                    if bill_type in results:
                        summary_data.append({
                            'חשבון': bill_name,
                            'דירה 1 (₪)': f"{results[bill_type]['apt1']['total']:.2f}",
                            'דירה 2 (₪)': f"{results[bill_type]['apt2']['total']:.2f}",
                            'סה״כ לחשבון (₪)': f"{results[bill_type]['total']:.2f}"
                        })
                
                # Add totals row
                total_apt1 = sum(r['apt1']['total'] for r in results.values())
                total_apt2 = sum(r['apt2']['total'] for r in results.values())
                total_all = sum(r['total'] for r in results.values())
                
                summary_data.append({
                    'חשבון': 'סה״כ לתשלום כולל',
                    'דירה 1 (₪)': f"{total_apt1:.2f}",
                    'דירה 2 (₪)': f"{total_apt2:.2f}",
                    'סה״כ לחשבון (₪)': f"{total_all:.2f}"
                })
                
                df = pd.DataFrame(summary_data)
                
                # Style the dataframe
                def highlight_total(row):
                    if row['חשבון'] == 'סה״כ לתשלום כולל':
                        return ['font-weight: bold'] * len(row)
                    return [''] * len(row)
                
                styled_df = df.style.apply(highlight_total, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
                # Export button
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 הורד כ-CSV",
                    data=csv,
                    file_name=f"bill_split_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
                # Save to history
                st.session_state.calculation_history.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'data': df.to_dict('records')
                })
                
                # Show detailed breakdown
                with st.expander("פירוט מלא"):
                    for bill_type, bill_name in bill_names.items():
                        if bill_type in results:
                            st.markdown(f"**{bill_name}:**")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("דירה 1:")
                                st.write(f"- חיובים קבועים: ₪{results[bill_type]['apt1']['fixed']:.2f}")
                                st.write(f"- עלות צריכה: ₪{results[bill_type]['apt1']['consumption']:.2f}")
                                st.write(f"- **סה״כ: ₪{results[bill_type]['apt1']['total']:.2f}**")
                            
                            with col2:
                                st.markdown("דירה 2:")
                                st.write(f"- חיובים קבועים: ₪{results[bill_type]['apt2']['fixed']:.2f}")
                                st.write(f"- עלות צריכה: ₪{results[bill_type]['apt2']['consumption']:.2f}")
                                st.write(f"- **סה״כ: ₪{results[bill_type]['apt2']['total']:.2f}**")
                            
                            st.markdown("---")
    
    with tab3:
        st.header("היסטוריית חישובים")
        
        if st.session_state.calculation_history:
            for calc in reversed(st.session_state.calculation_history):
                with st.expander(f"חישוב מתאריך: {calc['timestamp']}"):
                    df = pd.DataFrame(calc['data'])
                    st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("אין היסטוריית חישובים עדיין")

if __name__ == "__main__":
    main()
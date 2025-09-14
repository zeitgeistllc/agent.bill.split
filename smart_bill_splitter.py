# universal_bill_splitter.py
import streamlit as st
import pandas as pd
import time

# --- Page Configuration ---
st.set_page_config(page_title="Universal Bill Splitter", layout="wide")
st.title("🧾 Universal Bill Splitter")
st.write("Process your City Tax, Electricity, and Water bills from one place.")

# --- Session State Initialization ---
if 'processed_bills' not in st.session_state:
    st.session_state.processed_bills = []
    st.session_state.last_tax_result = None
    st.session_state.last_elec_result = None
    st.session_state.last_water_result = None

# Init keys for multi-step workflows if they don't exist
for prefix in ['elec', 'water']:
    if f'{prefix}_step' not in st.session_state:
        st.session_state[f'{prefix}_step'] = "upload"
        st.session_state[f'{prefix}_bill_data'] = None
        st.session_state[f'{prefix}_meter_reading'] = None
        st.session_state[f'{prefix}_previous_reading'] = None
        st.session_state[f'{prefix}_result_saved'] = False
        st.session_state[f'{prefix}_bill_name'] = ""

def reset_workflow(prefix):
    st.session_state[f'{prefix}_step'] = "upload"; st.session_state[f'{prefix}_bill_data'] = None; st.session_state[f'{prefix}_meter_reading'] = None
    st.session_state[f'{prefix}_previous_reading'] = None; st.session_state[f'{prefix}_result_saved'] = False; st.session_state[f'{prefix}_bill_name'] = ""
    st.rerun()

# --- Placeholder Functions for AI Processing ---
def simulate_meter_reading_ocr(meter_photo, unit):
    with st.spinner(f'AI is reading meter photo...'): time.sleep(1)
    return 8950.5 if unit == "kWh" else 415.0

def simulate_electricity_ocr_and_llm(bill_file, meter_file):
    with st.spinner('AI is analyzing electricity documents...'): time.sleep(1)
    return {'fixed_cost': 64.75, 'total_usage_cost': 1114.84, 'price_per_kwh': 0.5425, 'vat': 212.33}, {'current_reading_kwh': 9731.1}

def simulate_water_ocr_and_llm(bill_file, meter_file):
    with st.spinner('AI is analyzing water documents...'): time.sleep(1)
    return {'fixed_cost': 0.00, 'total_usage_cost': 306.86, 'price_per_m3': 9.30, 'vat': 55.23}, {'current_reading_m3': 1.0}

def simulate_tax_ocr_and_llm(tax_bill_file):
    with st.spinner('AI is analyzing tax document...'): time.sleep(1)
    return {'Arnona (Municipal Tax)': 1741.10, 'Shira (City Security)': 78.20}

# --- Sidebar for Grand Total ---
st.sidebar.title("Summary")
if st.session_state.processed_bills:
    st.sidebar.header("Processed Bills (Detail)")
    
    indices_to_remove = []
    for i, bill in enumerate(st.session_state.processed_bills):
        col1, col2 = st.sidebar.columns([0.9, 0.1])
        with col1:
            st.text(f"{bill['Bill Type']}: Apt 1: {bill['Apartment 1 (₪)']:.2f}, Apt 2: {bill['Apartment 2 (₪)']:.2f}")
        with col2:
            if st.checkbox("del", key=f"del_{i}", help="Mark to remove", label_visibility="collapsed"):
                indices_to_remove.append(i)
    
    if indices_to_remove:
        if st.sidebar.button("Remove Selected", type="primary"):
            st.session_state.processed_bills = [bill for i, bill in enumerate(st.session_state.processed_bills) if i not in indices_to_remove]
            st.rerun()

    st.sidebar.divider()
    
    st.sidebar.header("Totals by Category")
    summary_df = pd.DataFrame(st.session_state.processed_bills)
    summary_df['Category'] = summary_df['Bill Type'].apply(lambda x: x.split(' ')[0])
    
    subtotals_df = summary_df.groupby('Category')[['Apartment 1 (₪)', 'Apartment 2 (₪)']].sum()
    
    # <<< NEW: Add the total column for each category >>>
    subtotals_df['Category Total (₪)'] = subtotals_df['Apartment 1 (₪)'] + subtotals_df['Apartment 2 (₪)']
    
    if not subtotals_df.empty:
        grand_total = subtotals_df.sum()
        subtotals_df.loc['**GRAND TOTAL**'] = grand_total
    
    st.sidebar.dataframe(subtotals_df.style.format("{:.2f}"))
    
    if st.sidebar.button("Clear All Totals"):
        st.session_state.processed_bills = []; st.rerun()
else:
    st.sidebar.info("Your processed bills will be summarized here.")

# --- Main Page Layout ---

# --- Section 1: City Tax Bill ---
st.header("Split a City Tax (Arnona) Bill")
with st.container(border=True):
    tax_file = st.file_uploader("Upload your City Tax bill", type=['pdf', 'png', 'jpg', 'jpeg'], key="tax_uploader")
    
    if st.button("Process City Tax Bill"):
        if tax_file:
            tax_data = simulate_tax_ocr_and_llm(tax_file)
            df = pd.DataFrame.from_dict(tax_data, orient='index', columns=['Total Amount (₪)'])
            df.loc['**Total Payment**'] = df.sum()
            df['Apartment 1 (₪)'] = df['Total Amount (₪)'] / 2; df['Apartment 2 (₪)'] = df['Total Amount (₪)'] / 2
            st.subheader("City Tax Bill Breakdown"); st.dataframe(df.style.format("{:.2f}"), use_container_width=True)
            
            total_per_apt = df.loc['**Total Payment**', 'Apartment 1 (₪)']
            result = {'Bill Type': f'City Tax ({tax_file.name})', 'Apartment 1 (₪)': total_per_apt, 'Apartment 2 (₪)': total_per_apt}
            st.session_state.processed_bills.append(result)
            st.session_state.last_tax_result = result
            st.rerun()
        else: st.error("Please upload the city tax bill first.")

    if st.session_state.last_tax_result:
        if st.button("Add Last City Tax Again to Summary"):
            st.session_state.processed_bills.append(st.session_state.last_tax_result)
            st.rerun()

st.divider()

# --- Section 2: Electricity Bill ---
st.header("Split an Electricity Bill")
with st.container(border=True):
    if st.session_state.elec_step == "upload":
        st.subheader("Step 1: Upload Your Documents")
        with st.form("elec_upload_form"):
            bill_file = st.file_uploader("Upload the main electricity bill", key="elec_bill_up")
            current_meter_method = st.radio("Provide the **current** electricity meter reading by:", ("Uploading a photo", "Typing it manually"), horizontal=True, key="elec_current_radio")
            if current_meter_method == "Uploading a photo":
                meter_file = st.file_uploader("Upload photo of **current** electricity meter", key="elec_meter_up")
                manual_current_reading = None
            else:
                manual_current_reading = st.number_input("Enter **current** electricity meter reading (in kWh)", min_value=0.0, step=0.1, format="%.2f")
                meter_file = None

            if st.form_submit_button("Analyze Bill and Meter"):
                if not bill_file: st.error("Please upload the bill.")
                elif meter_file is None and (manual_current_reading is None or manual_current_reading <= 0): st.error("Please provide the current meter reading.")
                else:
                    bill_data, meter_data = simulate_electricity_ocr_and_llm(bill_file, meter_file)
                    if manual_current_reading is not None:
                        meter_data['current_reading_kwh'] = manual_current_reading
                    st.session_state.elec_step = "processing"; st.session_state.elec_bill_data, st.session_state.elec_meter_reading = bill_data, meter_data
                    st.session_state.elec_bill_name = bill_file.name; st.rerun()

    if st.session_state.elec_step == "processing":
        st.subheader("Step 2: Provide Previous Electricity Meter Reading")
        st.json({"From Bill": st.session_state.elec_bill_data, "From Meter Photo": st.session_state.elec_meter_reading})
        input_method = st.radio("Provide **previous** reading by:", ("Typing it manually", "Uploading a photo"), horizontal=True, key="elec_radio")
        with st.form("elec_input_form"):
            prev_reading_input = st.number_input("Previous meter reading (in kWh)?", min_value=0.0, step=0.1, format="%.2f") if input_method == "Typing it manually" else st.file_uploader("Upload photo of **previous** meter", key="elec_prev_meter_up")
            if st.form_submit_button("Calculate Bill Split"):
                final_prev_reading = prev_reading_input if input_method == "Typing it manually" else (simulate_meter_reading_ocr(prev_reading_input, "kWh") if prev_reading_input else None)
                if final_prev_reading is None: st.error("Provide previous reading.")
                elif final_prev_reading >= st.session_state.elec_meter_reading['current_reading_kwh']: st.error("Previous reading must be less than current.")
                else: st.session_state.elec_previous_reading = final_prev_reading; st.session_state.elec_step = "results"; st.session_state.elec_result_saved = False; st.rerun()

    if st.session_state.elec_step == "results":
        st.subheader("Step 3: Final Electricity Bill Split")
        bill, meter, prev_reading = st.session_state.elec_bill_data, st.session_state.elec_meter_reading, st.session_state.elec_previous_reading
        apt1_cost = (meter['current_reading_kwh'] - prev_reading) * bill['price_per_kwh']; apt2_cost, fixed_cost = bill['total_usage_cost'] - apt1_cost, bill['fixed_cost'] / 2
        subtotal1, subtotal2 = fixed_cost + apt1_cost, fixed_cost + apt2_cost; total_sub = bill['fixed_cost'] + bill['total_usage_cost']
        vat1, vat2 = (subtotal1 / total_sub) * bill['vat'], (subtotal2 / total_sub) * bill['vat']
        total1, total2 = subtotal1 + vat1, subtotal2 + vat2
        df = pd.DataFrame({"Cost Component": ["Fixed", "Usage", "VAT", "**Total**"], "Apt 1 (₪)": [fixed_cost, apt1_cost, vat1, total1], "Apt 2 (₪)": [fixed_cost, apt2_cost, vat2, total2], "Total (₪)": [bill['fixed_cost'], bill['total_usage_cost'], bill['vat'], total_sub + bill['vat']]}).set_index("Cost Component")
        st.dataframe(df.style.format("{:.2f}"), use_container_width=True)
        result = {'Bill Type': f'Electricity ({st.session_state.elec_bill_name})', 'Apartment 1 (₪)': total1, 'Apartment 2 (₪)': total2}
        if not st.session_state.elec_result_saved:
            st.session_state.processed_bills.append(result); st.session_state.last_elec_result = result
            st.session_state.elec_result_saved = True; st.rerun()
        col1, col2 = st.columns(2); col1.button("Process Another Electricity Bill", on_click=reset_workflow, args=('elec',), use_container_width=True, key="reset_elec")
        if st.session_state.last_elec_result: col2.button("Add This Bill Again to Summary", on_click=lambda: (st.session_state.processed_bills.append(st.session_state.last_elec_result), st.rerun()), use_container_width=True, key="readd_elec")

st.divider()

# --- Section 3: Water Bill ---
st.header("Split a Water Bill")
with st.container(border=True):
    if st.session_state.water_step == "upload":
        st.subheader("Step 1: Upload Your Documents")
        with st.form("water_upload_form"):
            bill_file = st.file_uploader("Upload the main water bill", key="water_bill_up")
            current_meter_method_water = st.radio("Provide the **current** water meter reading by:", ("Uploading a photo", "Typing it manually"), horizontal=True, key="water_current_radio")
            if current_meter_method_water == "Uploading a photo":
                meter_file_water = st.file_uploader("Upload photo of **current** water meter", key="water_meter_up")
                manual_current_reading_water = None
            else:
                manual_current_reading_water = st.number_input("Enter **current** water meter reading (in m³)", min_value=0.0, step=0.1, format="%.2f")
                meter_file_water = None
            if st.form_submit_button("Analyze Water Bill and Meter"):
                if not bill_file: st.error("Please upload the bill.")
                elif meter_file_water is None and (manual_current_reading_water is None or manual_current_reading_water <= 0): st.error("Please provide the current meter reading.")
                else:
                    bill_data, meter_data = simulate_water_ocr_and_llm(bill_file, meter_file_water)
                    if manual_current_reading_water is not None:
                        meter_data['current_reading_m3'] = manual_current_reading_water
                    st.session_state.water_step = "processing"; st.session_state.water_bill_data, st.session_state.water_meter_reading = bill_data, meter_data
                    st.session_state.water_bill_name = bill_file.name; st.rerun()

    if st.session_state.water_step == "processing":
        st.subheader("Step 2: Provide Previous Water Meter Reading")
        st.json({"From Bill": st.session_state.water_bill_data, "From Meter Photo": st.session_state.water_meter_reading})
        input_method = st.radio("Provide **previous** reading by:", ("Typing it manually", "Uploading a photo"), horizontal=True, key="water_radio")
        with st.form("water_input_form"):
            prev_reading_input = st.number_input("Previous meter reading (in m³)?", min_value=0.0, step=0.1, format="%.2f") if input_method == "Typing it manually" else st.file_uploader("Upload photo of **previous** meter", key="water_prev_meter_up")
            if st.form_submit_button("Calculate Water Bill Split"):
                final_prev_reading = prev_reading_input if input_method == "Typing it manually" else (simulate_meter_reading_ocr(prev_reading_input, "m³") if prev_reading_input else None)
                if final_prev_reading is None: st.error("Provide previous reading.")
                elif final_prev_reading >= st.session_state.water_meter_reading['current_reading_m3']: st.error("Previous reading must be less than current.")
                else: st.session_state.water_previous_reading = final_prev_reading; st.session_state.water_step = "results"; st.session_state.water_result_saved = False; st.rerun()
    
    if st.session_state.water_step == "results":
        st.subheader("Step 3: Final Water Bill Split")
        bill, meter, prev_reading = st.session_state.water_bill_data, st.session_state.water_meter_reading, st.session_state.water_previous_reading
        apt1_cost = (meter['current_reading_m3'] - prev_reading) * bill['price_per_m3']; apt2_cost, fixed_cost = bill['total_usage_cost'] - apt1_cost, bill['fixed_cost'] / 2
        subtotal1, subtotal2 = fixed_cost + apt1_cost, fixed_cost + apt2_cost; total_sub = bill['fixed_cost'] + bill['total_usage_cost']
        vat1, vat2 = (subtotal1 / total_sub) * bill['vat'], (subtotal2 / total_sub) * bill['vat']
        total1, total2 = subtotal1 + vat1, subtotal2 + vat2
        df = pd.DataFrame({"Cost Component": ["Fixed", "Usage", "VAT", "**Total**"], "Apt 1 (₪)": [fixed_cost, apt1_cost, vat1, total1], "Apt 2 (₪)": [fixed_cost, apt2_cost, vat2, total2], "Total (₪)": [bill['fixed_cost'], bill['total_usage_cost'], bill['vat'], total_sub + bill['vat']]}).set_index("Cost Component")
        st.dataframe(df.style.format("{:.2f}"), use_container_width=True)
        result = {'Bill Type': f'Water ({st.session_state.water_bill_name})', 'Apartment 1 (₪)': total1, 'Apartment 2 (₪)': total2}
        if not st.session_state.water_result_saved:
            st.session_state.processed_bills.append(result); st.session_state.last_water_result = result
            st.session_state.water_result_saved = True; st.rerun()
        col1, col2 = st.columns(2); col1.button("Process Another Water Bill", on_click=reset_workflow, args=('water',), use_container_width=True, key="reset_water")
        if st.session_state.last_water_result: col2.button("Add This Bill Again to Summary", on_click=lambda: (st.session_state.processed_bills.append(st.session_state.last_water_result), st.rerun()), use_container_width=True, key="readd_water")
import streamlit as st
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="מחשבון חלוקת חשבונות",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Functions ---

def calculate_split(bill_data):
    """
    Calculates the final bill split based on the input data.
    """
    results = {}

    # --- Arnona Calculation ---
    arnona_total = bill_data.get('arnona_total', 0)
    if arnona_total > 0:
        apt1_arnona = arnona_total / 2
        apt2_arnona = arnona_total / 2
        results['arnona'] = {
            'דירה 1': apt1_arnona,
            'דירה 2': apt2_arnona,
            'סה"כ לחשבון': arnona_total
        }

    # --- Electricity Calculation ---
    elec_total = bill_data.get('elec_total', 0)
    if elec_total > 0:
        elec_fixed = bill_data.get('elec_fixed', 0)
        total_kwh = bill_data.get('elec_total_kwh', 0)
        apt1_kwh = bill_data.get('elec_apt1_kwh', 0)

        # Ensure consumption for Apt 1 doesn't exceed total
        if apt1_kwh > total_kwh:
            st.error("שגיאה בחשמל: צריכת דירה 1 (קוט\"ש) גבוהה מסך הצריכה הכולל.")
            apt1_kwh = total_kwh # Cap it to avoid negative results

        consumption_cost = elec_total - elec_fixed
        apt2_kwh = total_kwh - apt1_kwh

        if total_kwh > 0:
            cost_per_kwh = consumption_cost / total_kwh
            apt1_consumption_cost = apt1_kwh * cost_per_kwh
            apt2_consumption_cost = apt2_kwh * cost_per_kwh
        else: # Handle case with no consumption
             cost_per_kwh = 0
             apt1_consumption_cost = 0
             apt2_consumption_cost = 0


        apt1_elec_total = (elec_fixed / 2) + apt1_consumption_cost
        apt2_elec_total = (elec_fixed / 2) + apt2_consumption_cost

        results['electricity'] = {
            'דירה 1': apt1_elec_total,
            'דירה 2': apt2_elec_total,
            'סה"כ לחשבון': elec_total
        }

    # --- Water Calculation ---
    water_total = bill_data.get('water_total', 0)
    if water_total > 0:
        water_fixed = bill_data.get('water_fixed', 0)
        total_m3 = bill_data.get('water_total_m3', 0)
        apt1_m3 = bill_data.get('water_apt1_m3', 0)

        # Ensure consumption for Apt 1 doesn't exceed total
        if apt1_m3 > total_m3:
            st.error("שגיאה במים: צריכת דירה 1 (מ\"ק) גבוהה מסך הצריכה הכולל.")
            apt1_m3 = total_m3 # Cap it to avoid negative results

        consumption_cost = water_total - water_fixed
        apt2_m3 = total_m3 - apt1_m3

        if total_m3 > 0:
            cost_per_m3 = consumption_cost / total_m3
            apt1_consumption_cost = apt1_m3 * cost_per_m3
            apt2_consumption_cost = apt2_m3 * cost_per_m3
        else: # Handle case with no consumption
            cost_per_m3 = 0
            apt1_consumption_cost = 0
            apt2_consumption_cost = 0

        apt1_water_total = (water_fixed / 2) + apt1_consumption_cost
        apt2_water_total = (water_fixed / 2) + apt2_consumption_cost

        results['water'] = {
            'דירה 1': apt1_water_total,
            'דירה 2': apt2_water_total,
            'סה"כ לחשבון': water_total
        }

    return results


def display_calculation_transparency(bill_data):
    """
    Displays the detailed calculation steps.
    """
    st.markdown("---")
    st.subheader("Transparent Calculation Breakdown")

    # --- Electricity Transparency ---
    if bill_data.get('elec_total', 0) > 0:
        with st.expander("פירוט חישוב חשמל"):
            elec_fixed = bill_data.get('elec_fixed', 0)
            elec_total = bill_data.get('elec_total', 0)
            total_kwh = bill_data.get('elec_total_kwh', 0)
            apt1_kwh = bill_data.get('elec_apt1_kwh', 0)
            apt2_kwh = total_kwh - apt1_kwh
            consumption_cost = elec_total - elec_fixed
            cost_per_kwh = consumption_cost / total_kwh if total_kwh > 0 else 0

            st.markdown(f"**עלות קבועה (50/50):** `{elec_fixed / 2:.2f} ₪` לכל דירה")
            st.markdown(f"**עלות צריכה כוללת:** `{consumption_cost:.2f} ₪` (`{elec_total:.2f}` - `{elec_fixed:.2f}`)")
            st.markdown(f"**מחיר לקוט\"ש:** `{cost_per_kwh:.4f} ₪` (`{consumption_cost:.2f} ₪` / `{total_kwh}` קוט\"ש)")
            st.markdown("---")
            st.markdown(f"**דירה 1:** `{elec_fixed / 2:.2f} ₪` (קבוע) + (`{apt1_kwh}` קוט\"ש * `{cost_per_kwh:.4f} ₪`) = **`{(elec_fixed / 2) + (apt1_kwh * cost_per_kwh):.2f} ₪`**")
            st.markdown(f"**דירה 2:** `{elec_fixed / 2:.2f} ₪` (קבוע) + (`{apt2_kwh}` קוט\"ש * `{cost_per_kwh:.4f} ₪`) = **`{(elec_fixed / 2) + (apt2_kwh * cost_per_kwh):.2f} ₪`**")

    # --- Water Transparency ---
    if bill_data.get('water_total', 0) > 0:
        with st.expander("פירוט חישוב מים"):
            water_fixed = bill_data.get('water_fixed', 0)
            water_total = bill_data.get('water_total', 0)
            total_m3 = bill_data.get('water_total_m3', 0)
            apt1_m3 = bill_data.get('water_apt1_m3', 0)
            apt2_m3 = total_m3 - apt1_m3
            consumption_cost = water_total - water_fixed
            cost_per_m3 = consumption_cost / total_m3 if total_m3 > 0 else 0

            st.markdown(f"**עלות קבועה (50/50):** `{water_fixed / 2:.2f} ₪` לכל דירה")
            st.markdown(f"**עלות צריכה כוללת:** `{consumption_cost:.2f} ₪` (`{water_total:.2f}` - `{water_fixed:.2f}`)")
            st.markdown(f"**מחיר למ\"ק:** `{cost_per_m3:.4f} ₪` (`{consumption_cost:.2f} ₪` / `{total_m3}` מ\"ק)")
            st.markdown("---")
            st.markdown(f"**דירה 1:** `{water_fixed / 2:.2f} ₪` (קבוע) + (`{apt1_m3}` מ\"ק * `{cost_per_m3:.4f} ₪`) = **`{(water_fixed / 2) + (apt1_m3 * cost_per_m3):.2f} ₪`**")
            st.markdown(f"**דירה 2:** `{water_fixed / 2:.2f} ₪` (קבוע) + (`{apt2_m3}` מ\"ק * `{cost_per_m3:.4f} ₪`) = **`{(water_fixed / 2) + (apt2_m3 * cost_per_m3):.2f} ₪`**")

# --- Main App Interface ---

st.title("GeminiGem 💎 - מחשבון חלוקת חשבונות")
st.markdown("הזן את הנתונים מהחשבונות וקריאות המונים כדי לחשב את החלוקה בין שתי הדירות.")

# Use session state to remember previous readings
if 'previous_readings' not in st.session_state:
    st.session_state.previous_readings = {'electricity': 0.0, 'water': 0.0}

# --- Sidebar for Previous Readings ---
with st.sidebar:
    st.header("⚙️ נתוני בסיס (נשמרים)")
    st.info("אלו קריאות המונה *הקודמות* של דירה 1. המערכת תזכור אותן לחישוב הבא.")
    prev_elec = st.number_input(
        "קריאת מונה חשמל קודמת (דירה 1)",
        key='prev_elec_reader',
        value=st.session_state.previous_readings['electricity'],
        step=0.1,
        format="%.1f"
    )
    prev_water = st.number_input(
        "קריאת מונה מים קודמת (דירה 1)",
        key='prev_water_reader',
        value=st.session_state.previous_readings['water'],
        step=0.1,
        format="%.1f"
    )
    # Update session state on change
    st.session_state.previous_readings['electricity'] = prev_elec
    st.session_state.previous_readings['water'] = prev_water


# --- Data Input Fields ---
bill_inputs = {}

# Using columns for a cleaner layout
col1, col2 = st.columns(2)

with col1:
    st.header("🏢 ארנונה")
    bill_inputs['arnona_total'] = st.number_input("סכום כולל לתשלום (₪)", key='arnona_total', min_value=0.0, step=10.0, value=1819.30)

with col2:
    st.header("💡 חשמל")
    bill_inputs['elec_total'] = st.number_input("סכום כולל לתשלום (₪)", key='elec_total', min_value=0.0, step=10.0, value=1391.92)
    bill_inputs['elec_fixed'] = st.number_input("סך תשלומים קבועים (₪)", key='elec_fixed', min_value=0.0, step=1.0, value=100.0)
    bill_inputs['elec_total_kwh'] = st.number_input("סך צריכה כוללת (קוט\"ש)", key='elec_total_kwh', min_value=0.0, step=5.0, value=2000.0)

    st.subheader("מונה דירה 1 (חשמל)")
    current_elec_reading = st.number_input("קריאת מונה נוכחית", key='elec_current', min_value=prev_elec, step=0.1, format="%.1f", value=prev_elec + 750.0)
    bill_inputs['elec_apt1_kwh'] = current_elec_reading - prev_elec
    st.metric(label="צריכת דירה 1 בתקופה זו", value=f"{bill_inputs['elec_apt1_kwh']:.1f} קוט\"ש")


with col1:
    st.header("💧 מים")
    bill_inputs['water_total'] = st.number_input("סכום כולל לתשלום (₪)", key='water_total', min_value=0.0, step=5.0, value=362.09)
    bill_inputs['water_fixed'] = st.number_input("סך תשלומים קבועים (₪)", key='water_fixed', min_value=0.0, step=1.0, value=30.0)
    bill_inputs['water_total_m3'] = st.number_input("סך צריכה כוללת (מ\"ק)", key='water_total_m3', min_value=0.0, step=1.0, value=45.0)

    st.subheader("מונה דירה 1 (מים)")
    current_water_reading = st.number_input("קריאת מונה נוכחית", key='water_current', min_value=prev_water, step=0.1, format="%.1f", value=prev_water + 2.0)
    bill_inputs['water_apt1_m3'] = current_water_reading - prev_water
    st.metric(label="צריכת דירה 1 בתקופה זו", value=f"{bill_inputs['water_apt1_m3']:.1f} מ\"ק")


# --- Calculation and Display ---
if st.button("חשב חלוקה", type="primary", use_container_width=True):
    results = calculate_split(bill_inputs)

    if results:
        st.markdown("---")
        st.header("📊 טבלת סיכום וחלוקה")

        # Prepare data for DataFrame
        data_for_df = {
            'חשמל': [
                f"{results.get('electricity', {}).get('דירה 1', 0):.2f}",
                f"{results.get('electricity', {}).get('דירה 2', 0):.2f}",
                f"{results.get('electricity', {}).get('סה\"כ לחשבון', 0):.2f}"
            ],
            'ארנונה': [
                f"{results.get('arnona', {}).get('דירה 1', 0):.2f}",
                f"{results.get('arnona', {}).get('דירה 2', 0):.2f}",
                f"{results.get('arnona', {}).get('סה\"כ לחשבון', 0):.2f}"
            ],
            'מים': [
                f"{results.get('water', {}).get('דירה 1', 0):.2f}",
                f"{results.get('water', {}).get('דירה 2', 0):.2f}",
                f"{results.get('water', {}).get('סה\"כ לחשבון', 0):.2f}"
            ]
        }

        index_labels = ['דירה 1 (₪)', 'דירה 2 (₪)', 'סה"כ לחשבון (₪)']
        df = pd.DataFrame(data_for_df, index=index_labels).T # Transpose for correct layout

        # Calculate totals
        total_apt1 = sum(res.get('דירה 1', 0) for res in results.values())
        total_apt2 = sum(res.get('דירה 2', 0) for res in results.values())
        grand_total = sum(res.get('סה"כ לחשבון', 0) for res in results.values())

        # Add total row
        df.loc['סה"כ לתשלום כולל'] = [f"{total_apt1:.2f}", f"{total_apt2:.2f}", f"{grand_total:.2f}"]

        # Display the styled table
        st.dataframe(df.style.apply(lambda x: ['background-color: #f0f2f6' if i == len(x)-1 else '' for i, v in enumerate(x)], axis=0)
                       .apply(lambda x: ['font-weight: bold' if x.name == 'סה"כ לתשלום כולל' else '' for i in x], axis=1),
                       use_container_width=True)

        # Export to CSV (compatible with Sheets)
        @st.cache_data
        def convert_df_to_csv(df_to_convert):
            return df_to_convert.to_csv(index=True).encode('utf-8-sig')

        csv = convert_df_to_csv(df)
        st.download_button(
           label="📥 Export to CSV (for Sheets)",
           data=csv,
           file_name='bill_split_summary.csv',
           mime='text/csv',
           use_container_width=True
        )

        # Display transparency section
        display_calculation_transparency(bill_inputs)
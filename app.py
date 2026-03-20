import streamlit as st
import pandas as pd
import re
import os

# --- LUHN ALGORITHM ---
def calculate_luhn(base14):
    digits = [int(d) for d in str(base14)]
    for i in range(len(digits) - 1, -1, -2):
        doubled = digits[i] * 2
        digits[i] = doubled if doubled <= 9 else (doubled // 10) + (doubled % 10)
    return str((10 - (sum(digits) % 10)) % 10)

# --- DATA LOADER ---
@st.cache_data
def load_preset_database():
    """Loads the CSV database from the same folder as the script."""
    csv_path = "samsung_offsets.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # Convert TAC_Prefix to string to ensure matching works
        df['TAC_Prefix'] = df['TAC_Prefix'].astype(str)
        return dict(zip(df['TAC_Prefix'], df['Expected_Offset']))
    return {}

# --- APP SETUP ---
st.set_page_config(page_title="Samsung IMEI Converter", layout="wide")
st.title("📱 Samsung IMEI Converter (Database Enabled)")

# Load the database automatically
db_offsets = load_preset_database()
if db_offsets:
    st.sidebar.success(f"Loaded {len(db_offsets)} model offsets from database.")
else:
    st.sidebar.warning("No samsung_offsets.csv found. Using manual calibration only.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Calibration (Paste Examples)")
    cal_input = st.text_area("Paste side-by-side columns (IMEI 1 | IMEI 2):", height=200)

with col2:
    st.subheader("2. Target (Paste IMEI 1 List)")
    batch_input = st.text_area("Paste new IMEI 1s to convert:", height=200)

if batch_input:
    # 1. Start with database offsets
    active_tac_map = db_offsets.copy()
    
    # 2. Add/Override with Manual Calibration
    if cal_input:
        lines = cal_input.strip().split('\n')
        for line in lines:
            row_imeis = re.findall(r'\b\d{15}\b', line)
            if len(row_imeis) >= 2:
                i1, i2 = row_imeis[0], row_imeis[1]
                tac = i1[:8]
                offset = int(i2[:14]) - int(i1[:14])
                active_tac_map[tac] = offset
    
    # 3. Process Batch
    target_imeis = re.findall(r'\b\d{15}\b', batch_input)
    results = []
    
    for i1 in target_imeis:
        tac_8 = i1[:8]
        tac_6 = i1[:6] # Some older models use 6-digit TACs
        
        # Priority: Exact 8-digit match > 6-digit match > Default (+8)
        offset = active_tac_map.get(tac_8, active_tac_map.get(tac_6, 8))
        
        base14 = i1[:14]
        new_base = str(int(base14) + offset).zfill(14)
        i2 = new_base + calculate_luhn(new_base)
        
        results.append({
            "IMEI 1": i1,
            "IMEI 2": i2,
            "TAC": tac_8,
            "Offset Applied": f"{offset:+}",
            "Source": "Manual" if tac_8 in active_tac_map and cal_input else ("Database" if tac_8 in db_offsets else "Default")
        })

    if results:
        df_res = pd.DataFrame(results)
        st.divider()
        st.dataframe(df_res, use_container_width=True)
        st.download_button("Download CSV", df_res.to_csv(index=False), "imei_results.csv")

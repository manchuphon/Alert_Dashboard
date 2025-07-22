import streamlit as st
import pandas as pd
import joblib
from modules.data_loader import load_all_data
from modules.train_cost_progress_model import extract_cost_progress_features

# ==== โหลดข้อมูลทั้งหมด ====
data = load_all_data("data1")

# ==== เตรียม project_id ทั้งหมดให้เป็น string และ strip ช่องว่าง ====
projects_df = data['projects']
projects_df['project_id'] = projects_df['project_id'].astype(str).str.strip()
for key, df in data.items():
    if 'project_id' in df.columns:
        data[key]['project_id'] = df['project_id'].astype(str).str.strip()

project_ids = sorted(projects_df['project_id'].unique())
selected_project = st.selectbox("เลือกโครงการ", project_ids, index=0, placeholder="พิมพ์รหัสโครงการ...")

# ==== กรองข้อมูลตามโครงการที่เลือก ====
project_data = {
    k: df[df['project_id'] == selected_project]
    for k, df in data.items()
    if 'project_id' in df.columns
}

# ==== ส่วนหัว ====
st.title("📊 AI Budget Alert Dashboard")
st.markdown(f"### 📁 โครงการที่เลือก: `{selected_project}`")

# ==== วิเคราะห์ Cost vs Progress ====
st.subheader("📈 วิเคราะห์ Cost vs Progress")

try:
    cost_model = joblib.load("saved_models/cost_progress_model.pkl")
except FileNotFoundError:
    cost_model = None
    st.warning("❗ ไม่พบโมเดล cost_progress_model.pkl กรุณาฝึกโมเดลก่อน")

# สร้างฟีเจอร์
progress_pct, spent_pct = extract_cost_progress_features(project_data)

col1, col2 = st.columns(2)
col1.metric("ความคืบหน้า (%)", f"{progress_pct}%")
col2.metric("ใช้จ่ายจริง (%)", f"{spent_pct}%")

# พยากรณ์ด้วยโมเดล
if cost_model:
    result = cost_model.predict([[progress_pct, spent_pct]])[0]
    prediction_text = "⚠️ ผิดปกติ: ค่าใช้จ่ายสูงเกินความคืบหน้า" if result == 1 else "✅ ปกติ"
    st.info(f"📌 ผลประเมินจาก AI: {prediction_text}")

# ==== วิเคราะห์ Vendor ====
st.subheader("📦 วิเคราะห์ Vendor ว่าจะจ่ายตรงเวลาหรือไม่")

try:
    vendor_model = joblib.load("saved_models/vendor_model.pkl")
except FileNotFoundError:
    vendor_model = None
    st.warning("❗ ไม่พบโมเดล vendor_model.pkl กรุณาฝึกโมเดลก่อน")

if vendor_model:
    vendor_df = data['vendors']
    expense_df = project_data.get('expenses', pd.DataFrame())

    if not expense_df.empty:
        vendor_used = expense_df['vendor'].dropna().unique()
        vendor_info = vendor_df[vendor_df['vendor_name'].isin(vendor_used)].copy()

        if not vendor_info.empty:
            used_features = ['rating', 'payment_terms', 'total_contracts', 'total_value']
            vendor_features = vendor_info[['vendor_name'] + used_features].copy()
            vendor_features = pd.get_dummies(vendor_features, columns=['rating', 'payment_terms'], drop_first=True)

            # เพิ่ม missing columns ที่โมเดลต้องใช้
            for col in vendor_model.feature_names_in_:
                if col not in vendor_features.columns:
                    vendor_features[col] = 0

            vendor_features = vendor_features[vendor_model.feature_names_in_]
            preds = vendor_model.predict(vendor_features)
            probs = vendor_model.predict_proba(vendor_features)[:, 1]

            vendor_info['on_time_prediction'] = preds
            vendor_info['on_time_probability'] = (probs * 100).round(2)
            vendor_info['สถานะ'] = vendor_info['on_time_prediction'].map({1: '✅ ตรงเวลา', 0: '⚠️ อาจล่าช้า'})

            st.dataframe(vendor_info[['vendor_name', 'rating', 'payment_terms',
                                      'total_contracts', 'total_value', 'สถานะ', 'on_time_probability']],
                         use_container_width=True)
        else:
            st.info("ℹ️ ไม่พบข้อมูล Vendor ของโครงการนี้ใน vendors.csv")
    else:
        st.info("ℹ️ โครงการนี้ไม่มีข้อมูล Expense")

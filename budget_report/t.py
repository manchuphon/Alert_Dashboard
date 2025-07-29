import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# เชื่อมต่อ PostgreSQL
engine = create_engine("postgresql://your_user:your_password@your_host:your_port/your_db")

# โหลดข้อมูล
summary_query = "SELECT * FROM summary_costs"
actual_query = "SELECT * FROM actual_costs"

summary_df = pd.read_sql(summary_query, engine)
actual_df = pd.read_sql(actual_query, engine)

# รวมข้อมูล: merge จาก g_code และ s_code
merged_df = pd.merge(summary_df, actual_df, on=['g_code', 's_code'], how='left')

# สร้างหน้า Streamlit
st.title("🔍 Construction Budget vs Actual Analysis")

# สร้าง Filter dropdown
g_code_options = ['ทั้งหมด'] + sorted(merged_df['g_code'].dropna().unique().tolist())
selected_g_code = st.selectbox("เลือก G-Code", g_code_options)

if selected_g_code != 'ทั้งหมด':
    filtered_df = merged_df[merged_df['g_code'] == selected_g_code]
else:
    filtered_df = merged_df.copy()

s_code_options = ['ทั้งหมด'] + sorted(filtered_df['s_code'].dropna().unique().tolist())
selected_s_code = st.selectbox("เลือก S-Code", s_code_options)

if selected_s_code != 'ทั้งหมด':
    filtered_df = filtered_df[filtered_df['s_code'] == selected_s_code]

# คำนวณ summary
filtered_df['boq'] = pd.to_numeric(filtered_df['boq'], errors='coerce')
filtered_df['actual_cost_all'] = pd.to_numeric(filtered_df['actual_cost_all'], errors='coerce')

total_budget = filtered_df['boq'].sum()
total_actual = filtered_df['actual_cost_all'].sum()
usage_percent = (total_actual / total_budget * 100) if total_budget else 0
remaining = total_budget - total_actual

# แสดงผล
st.metric("📋 งบประมาณรวม (BOQ)", f"{total_budget:,.2f} บาท")
st.metric("💸 ใช้จริงทั้งหมด", f"{total_actual:,.2f} บาท")
st.metric("📊 ใช้งบไปแล้ว (%)", f"{usage_percent:.2f} %")
st.metric("💼 งบคงเหลือ", f"{remaining:,.2f} บาท")

st.divider()
st.subheader("📑 รายละเอียดงบประมาณและต้นทุน")

st.dataframe(filtered_df[[
    'g_code', 's_code', 'description', 'boq', 
    'actual_cost_all', 'budget_balance_ac', 'variance_budget'
]].rename(columns={
    'g_code': 'G-Code',
    's_code': 'S-Code',
    'description': 'รายละเอียด',
    'boq': 'งบประมาณ (BOQ)',
    'actual_cost_all': 'ต้นทุนที่ใช้จริง',
    'budget_balance_ac': 'งบคงเหลือหลังใช้จริง',
    'variance_budget': 'งบเหลื่อมล้ำ (Variance)'
}))

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(layout="wide", page_title="วิเคราะห์ต้นทุนโครงการก่อสร้าง")

# Function to load data from database
@st.cache_data(show_spinner=False)
def load_data_from_db(table_name):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        if table_name == "actual_costs":
            query = """
            SELECT g_code, s_code, description, boq, total_budget, total_actual, bg_balance,
                   ac_material, ac_subcontract, pg_submit_balance, "to",
                   bg_overhead, bg_material, bg_labour, bg_subcontract,
                   ac_overhead, ac_labour, pg_submit, pg_certificate,
                   created_at, updated_at
            FROM actual_costs
            WHERE total_budget IS NOT NULL AND total_actual IS NOT NULL
            """
        elif table_name == "summary_costs":
            query = """
            SELECT id, g_code, s_code, description, boq, budget, cost_saving, purchase_cost,
                   pr_pending, budget_balance_pu, actual_cost_ac, unbook, actual_cost_all,
                   budget_balance_ac, purchase_balance, forecast, to_be_order, variance_budget,
                   finance_cost, finance_balance, "to", created_at, updated_at
            FROM summary_costs
            """
        elif table_name == "progress_payments":
            query = """
            SELECT project_no, project_name, year, month, payment_date, period,
                   progress_submit, certificate, submit_balance, remark, ref_no, no,
                   created_at, updated_at
            FROM progress_payments
            """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูลจากตาราง {table_name}: {str(e)}")
        return pd.DataFrame()

# Load data from multiple tables
df_actual = load_data_from_db("actual_costs")
df_summary = load_data_from_db("summary_costs")
df_payment = load_data_from_db("progress_payments")

# Check if DataFrames are empty
if df_actual.empty:
    st.error("ไม่สามารถโหลดข้อมูลจากตาราง actual_costs ได้ กรุณาตรวจสอบฐานข้อมูล")
    st.stop()
if df_summary.empty:
    st.warning("⚠️ ไม่มีข้อมูลจากตาราง summary_costs")
if df_payment.empty:
    st.warning("⚠️ ไม่มีข้อมูลจากตาราง progress_payments")

# Rename columns for consistency in actual_costs
df_actual = df_actual.rename(columns={
    'pg_certificate': 'bcwp',
    'pg_submit': 'ev',
    'to': 'to_column'
})

# Data preprocessing for actual_costs
numeric_cols = [
    'total_budget', 'total_actual', 'bcwp', 'ev', 'bg_balance',
    'boq', 'bg_overhead', 'bg_material', 'bg_labour', 'bg_subcontract',
    'ac_overhead', 'ac_material', 'ac_labour', 'ac_subcontract',
    'pg_submit_balance'
]
available_cols = [col for col in numeric_cols if col in df_actual.columns]
for col in available_cols:
    df_actual[col] = pd.to_numeric(df_actual[col], errors='coerce')

# Calculate percentage variance
df_actual['variance_percentage'] = (df_actual['bg_balance'] / df_actual['total_budget'] * 100).round(2).fillna(0)

# Handle NULL values in 'to_column' for treemap
df_actual['to_column'] = df_actual['to_column'].fillna('root')

# Create hierarchy label for treemap
df_actual['hierarchy_label'] = df_actual.apply(
    lambda row: f"{row['g_code']}: {row['description']}" if pd.isna(row['s_code'])
    else f"{row['g_code']}-{row['s_code']}: {row['description']}", axis=1
)

# Preprocess progress_payments: Create datetime column
if not df_payment.empty:
    df_payment['payment_date'] = pd.to_datetime(df_payment['payment_date'])
    df_payment['year_month'] = df_payment['payment_date'].dt.to_period('M').astype(str)

# Preprocess summary_costs: Calculate variance percentage
if not df_summary.empty:
    df_summary['variance_pct'] = (df_summary['variance_budget'] / df_summary['budget'] * 100).round(2).fillna(0)

# Sidebar for analysis selection
st.sidebar.title("เมนูวิเคราะห์")
analysis_type = st.sidebar.selectbox(
    "เลือกประเภทการวิเคราะห์",
    [
        "👀 ภาพรวมต้นทุนทั้งหมด",
        "📈 เปรียบเทียบงบประมาณกับค่าใช้จริง",
        "🚨 รายการที่มีความเสี่ยงสูง",
        "💰 สถานะการเบิกเงิน",
        "🌳 การกระจายต้นทุนตามลำดับชั้น",
        "📊 ตัวชี้วัดการจัดการโปรเจกต์",
        "📅 แนวโน้มการเบิกเงินและรับรอง",
        "🏗 เปรียบเทียบหลายโปรเจกต์"
    ]
)

# Additional Filter
st.sidebar.markdown("---")
st.sidebar.subheader("ตัวกรองเพิ่มเติม")
category_filter = st.sidebar.multiselect(
    "เลือกหมวดงาน (g_code) - สำหรับ actual_costs และ summary_costs",
    options=df_actual['g_code'].unique() if not df_actual.empty else [],
    default=df_actual['g_code'].unique() if not df_actual.empty else []
)
project_filter = st.sidebar.multiselect(
    "เลือกโปรเจกต์ - สำหรับ progress_payments",
    options=df_payment['project_no'].unique() if not df_payment.empty else [],
    default=df_payment['project_no'].unique() if not df_payment.empty else []
)

# Apply filters
if category_filter:
    df_actual = df_actual[df_actual['g_code'].isin(category_filter)]
    if not df_summary.empty:
        df_summary = df_summary[df_summary['g_code'].isin(category_filter)]
if project_filter:
    if not df_payment.empty:
        df_payment = df_payment[df_payment['project_no'].isin(project_filter)]

# Main title and description
st.title("📊 รายงานวิเคราะห์ต้นทุนโครงการก่อสร้าง")
st.markdown("เหมาะสำหรับผู้บริหาร (CEO, CFO, PM) เพื่อประเมินความคุ้มค่าและความเสี่ยงของโครงการก่อสร้าง")

# Analysis Sections
if analysis_type == "📊 ตัวชี้วัดการจัดการโปรเจกต์":
    st.subheader("📊 ตัวชี้วัดการจัดการโปรเจกต์ (CPI, SPI, EAC)")
    df_filtered = df_actual[df_actual['g_code'].isin(category_filter)] if category_filter else df_actual
    total_budget = df_filtered['total_budget'].sum()
    acwp = df_filtered['total_actual'].sum()
    bcwp = df_filtered['bcwp'].sum()
    ev = df_filtered['ev'].sum()
    cpi = bcwp / acwp if acwp != 0 else 0
    spi = bcwp / ev if ev != 0 else 0
    eac = acwp + (total_budget - bcwp)
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Budget (BAC)", f"฿{total_budget:,.2f}")
    col2.metric("📦 ACWP (Actual Cost)", f"฿{acwp:,.2f}")
    col3.metric("📌 BCWP (Earned Value)", f"฿{bcwp:,.2f}")
    col4, col5, col6 = st.columns(3)
    col4.metric("⚙️ CPI (Cost Performance Index)", f"{cpi:.2f}")
    col5.metric("⏱ SPI (Schedule Performance Index)", f"{spi:.2f}")
    col6.metric("🔮 EAC (Estimate at Completion)", f"฿{eac:,.2f}")
    indices_df = pd.DataFrame({"ตัวชี้วัด": ["CPI", "SPI"], "ค่า": [cpi, spi]})
    fig_indices = px.bar(indices_df, x="ตัวชี้วัด", y="ค่า", title="เปรียบเทียบ CPI และ SPI",
                         color="ตัวชี้วัด", color_discrete_sequence=['#1f77b4', '#ff7f0e'],
                         labels={'ค่า': 'ค่า index'})
    fig_indices.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="เกณฑ์ 1.0")
    st.plotly_chart(fig_indices, use_container_width=True)
    st.markdown("### ข้อมูลที่ใช้คำนวณ")
    st.dataframe(df_filtered[['g_code', 's_code', 'description', 'total_budget', 'total_actual', 'bcwp', 'ev']])
    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CPI < 1**: โครงการมีค่าใช้จ่ายเกินงบประมาณ
    - **SPI < 1**: โครงการล่าช้ากว่ากำหนด
    - **EAC**: คาดการณ์ต้นทุนรวมเมื่อสิ้นสุดโครงการ
    """)

elif analysis_type == "👀 ภาพรวมต้นทุนทั้งหมด":
    st.subheader("🔍 ภาพรวมต้นทุนทั้งหมด")
    df_s = df_actual[df_actual['s_code'].notna()].copy()
    total_budget = df_s['total_budget'].sum()
    total_actual = df_s['total_actual'].sum()
    total_balance = df_s['bg_balance'].sum()
    total_submit = df_s['ev'].sum()
    total_certificate = df_s['bcwp'].sum()
    total_uncertified = df_s['pg_submit_balance'].sum()
    variance_pct = (total_balance / total_budget * 100) if total_budget > 0 else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 งบประมาณรวม", f"฿{total_budget:,.2f}")
    col2.metric("💸 ค่าใช้จ่ายจริงรวม", f"฿{total_actual:,.2f}")
    col3.metric("✅ งบคงเหลือ", f"฿{total_balance:,.2f}", delta="Positive" if total_balance > 0 else "Negative")
    col4, col5, col6 = st.columns(3)
    col4.metric("🧾 ยอดเบิกเงินทั้งหมด", f"฿{total_submit:,.2f}")
    col5.metric("📜 ยอดที่รับรองแล้ว", f"฿{total_certificate:,.2f}")
    col6.metric("⏳ ยอดรอรับรอง", f"฿{total_uncertified:,.2f}")
    pie_df = pd.DataFrame({
        "ประเภท": ["ค่าใช้จริง", "งบคงเหลือ"],
        "จำนวนเงิน": [total_actual, total_balance if total_balance > 0 else 0]
    })
    fig_pie = px.pie(pie_df, names="ประเภท", values="จำนวนเงิน", title="โครงสร้างการใช้จ่าย",
                     color_discrete_sequence=['#ff7f0e', '#2ca02c'])
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CEO**: ภาพรวมนี้แสดงถึงสุขภาพทางการเงินของโครงการ
    - **CFO**: ยอดรอรับรองสูงอาจบ่งบอกถึงความล่าช้าในการรับเงิน
    - **PM**: เปรียบเทียบค่าใช้จริงกับงบประมาณเพื่อวางแผนการใช้จ่าย
    """)

elif analysis_type == "🚨 รายการที่มีความเสี่ยงสูง":
    st.subheader("⚠️ รายการที่มีความเสี่ยงสูง")
    st.markdown(f"**Debug**: จำนวนแถวใน df_actual: {len(df_actual)}")
    risk_df = df_actual[(df_actual['bg_balance'] < 0) | (df_actual['pg_submit_balance'] > 1000000)][
        ['g_code', 's_code', 'description', 'total_budget', 'total_actual', 'bg_balance', 'variance_percentage', 'pg_submit_balance']
    ].copy()
    st.markdown(f"**Debug**: จำนวนแถวที่มีความเสี่ยงสูง: {len(risk_df)}")
    if risk_df.empty:
        st.success("✅ ไม่มีรายการที่มีความเสี่ยงสูง")
    else:
        st.warning(f"พบ {len(risk_df)} รายการที่มีความเสี่ยงสูง")
        risk_df['variance_percentage'] = risk_df['variance_percentage'].apply(lambda x: f"{x:.2f}%")
        st.dataframe(risk_df.style.format({
            "total_budget": "{:,.2f}", "total_actual": "{:,.2f}", 
            "bg_balance": "{:,.2f}", "pg_submit_balance": "{:,.2f}"
        }), use_container_width=True)
        over_budget = df_actual[df_actual['bg_balance'] < 0].copy()
        if not over_budget.empty:
            top10 = over_budget.sort_values('bg_balance').head(10)
            fig_top10 = px.bar(
                top10, x='description', y='bg_balance', color='bg_balance',
                title="10 รายการที่ใช้จ่ายเกินงบมากที่สุด",
                labels={'bg_balance': 'งบคงเหลือ (บาท)'}, color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_top10, use_container_width=True)
        st.markdown("""
        **ข้อมูลเชิงลึก**:
        - **CEO**: รายการที่มีความเสี่ยงสูงต้องได้รับการตรวจสอบ
        - **CFO**: รายการที่มี pg_submit_balance สูงอาจบ่งบอกถึงปัญหาการเงินสด
        - **PM**: รายการที่เกินงบอาจต้องปรับแผนงานหรือควบคุมการใช้วัสดุ
        """)

elif analysis_type == "💰 สถานะการเบิกเงิน":
    st.subheader("💰 สถานะการเบิกเงินและรับรอง")
    st.markdown(f"**Debug**: จำนวนแถวใน df_actual: {len(df_actual)}")
    payment_df = df_actual[df_actual['ev'] > 0][['g_code', 's_code', 'description', 'ev', 'bcwp']].copy()
    st.markdown(f"**Debug**: จำนวนแถวที่มี ev > 0: {len(payment_df)}")
    if payment_df.empty:
        st.warning("⚠️ ไม่มีข้อมูลการเบิกเงิน (ev > 0) ในข้อมูลที่เลือก")
        st.markdown("**Debug**: สรุป ev และ bcwp")
        st.write(df_actual[['ev', 'bcwp']].describe())
    else:
        payment_df['certification_rate'] = (payment_df['bcwp'] / payment_df['ev'] * 100).round(2)
        fig_payment = px.bar(
            payment_df, x='description', y=['ev', 'bcwp'],
            title="การเบิกเงินและรับรองตามรายการ",
            barmode='group', labels={'value': 'จำนวนเงิน (บาท)', 'description': 'รายการ'},
            color_discrete_map={'ev': '#1f77b4', 'bcwp': '#ff7f0e'}
        )
        st.plotly_chart(fig_payment, use_container_width=True)
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=payment_df['description'], y=payment_df['ev'], name="ยอดเบิก",
            mode='lines+markers', line=dict(color='#1f77b4')
        ))
        fig_line.add_trace(go.Scatter(
            x=payment_df['description'], y=payment_df['bcwp'], name="ยอดรับรอง",
            mode='lines+markers', line=dict(color='#ff7f0e')
        ))
        fig_line.update_layout(
            title="ความคืบหน้าการรับรองการเบิกเงิน",
            xaxis_title="รายการ", yaxis_title="จำนวนเงิน (บาท)",
            template='plotly_white'
        )
        st.plotly_chart(fig_line, use_container_width=True)
        st.dataframe(payment_df[['g_code', 's_code', 'description', 'ev', 'bcwp', 'certification_rate']].style.format({
            "ev": "{:,.2f}", "bcwp": "{:,.2f}", "certification_rate": "{:.2f}%"
        }), use_container_width=True)
        st.markdown("""
        **ข้อมูลเชิงลึก**:
        - **CEO**: การรับรองที่ล่าช้าอาจส่งผลต่อความน่าเชื่อถือของโครงการ
        - **CFO**: ควรติดตามยอดรอรับรองเพื่อให้มั่นใจว่าเงินสดเพียงพอ
        - **PM**: ตรวจสอบรายการที่มีอัตราการรับรองต่ำเพื่อแก้ไขปัญหาการส่งมอบงาน
        """)

elif analysis_type == "🌳 การกระจายต้นทุนตามลำดับชั้น":
    st.subheader("🌳 การกระจายต้นทุนตามลำดับชั้น")
    df_s = df_actual[df_actual['s_code'].notna()].copy()
    fig_treemap = px.treemap(
        df_s, path=['to_column', 'g_code', 's_code'], values='total_actual',
        title="การกระจายต้นทุนตามลำดับชั้น",
        color='variance_percentage', color_continuous_scale='RdYlGn',
        labels={'total_actual': 'ค่าใช้จ่ายจริง (บาท)', 'variance_percentage': 'เปอร์เซ็นต์ความแปรปรวน'}
    )
    st.plotly_chart(fig_treemap, use_container_width=True)
    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CEO**: เห็นภาพรวมการกระจายต้นทุนตามโครงสร้างงาน
    - **CFO**: ระบุหมวดงานที่มีค่าใช้จ่ายสูงเพื่อควบคุมงบ
    - **PM**: ใช้เพื่อตรวจสอบว่าแต่ละหมวดงานอยู่ในงบหรือไม่
    """)

elif analysis_type == "📅 แนวโน้มการเบิกเงินและรับรอง":
    st.subheader("📅 แนวโน้มการเบิกเงินและรับรองตามเวลา")
    if df_payment.empty:
        st.warning("⚠️ ไม่มีข้อมูลการเบิกเงินในตาราง progress_payments")
    else:
        st.markdown(f"**Debug**: จำนวนแถวใน progress_payments: {len(df_payment)}")
        trend_df = df_payment.groupby('year_month')[['progress_submit', 'certificate', 'submit_balance']].sum().reset_index()
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=trend_df['year_month'], y=trend_df['progress_submit'], name="ยอดเบิก",
            mode='lines+markers', line=dict(color='#1f77b4')
        ))
        fig_trend.add_trace(go.Scatter(
            x=trend_df['year_month'], y=trend_df['certificate'], name="ยอดรับรอง",
            mode='lines+markers', line=dict(color='#ff7f0e')
        ))
        fig_trend.add_trace(go.Scatter(
            x=trend_df['year_month'], y=trend_df['submit_balance'], name="ยอดรอรับรอง",
            mode='lines+markers', line=dict(color='#d62728')
        ))
        fig_trend.update_layout(
            title="แนวโน้มการเบิกเงินและรับรองตามเวลา",
            xaxis_title="ปี-เดือน", yaxis_title="จำนวนเงิน (บาท)",
            template='plotly_white'
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.dataframe(trend_df.style.format({
            "progress_submit": "{:,.2f}", "certificate": "{:,.2f}", "submit_balance": "{:,.2f}"
        }), use_container_width=True)
        st.markdown("""
        **ข้อมูลเชิงลึก**:
        - **CEO**: แนวโน้มยอดรอรับรองสูงอาจบ่งบอกถึงปัญหาการเงินสด
        - **CFO**: ช่วงที่มีช่องว่างระหว่างยอดเบิกและยอดรับรองมาก ควรเร่งเจรจากับผู้ว่าจ้าง
        - **PM**: ตรวจสอบงานในช่วงที่มีการรับรองต่ำเพื่อแก้ไขปัญหาการส่งมอบ
        """)

elif analysis_type == "🏗 เปรียบเทียบหลายโปรเจกต์":
    st.subheader("🏗 เปรียบเทียบหลายโปรเจกต์")
    if df_summary.empty:
        st.warning("⚠️ ไม่มีข้อมูลในตาราง summary_costs")
    else:
        st.markdown(f"**Debug**: จำนวนแถวใน summary_costs: {len(df_summary)}")
        fig_compare = px.bar(
            df_summary, x='description', y=['budget', 'actual_cost_ac', 'budget_balance_ac'],
            title="เปรียบเทียบงบประมาณ ค่าใช้จ่ายจริง และงบคงเหลือระหว่างหมวดงาน",
            barmode='group', labels={'value': 'จำนวนเงิน (บาท)', 'description': 'หมวดงาน'},
            color_discrete_map={'budget': '#1f77b4', 'actual_cost_ac': '#ff7f0e', 'budget_balance_ac': '#2ca02c'}
        )
        st.plotly_chart(fig_compare, use_container_width=True)
        st.dataframe(df_summary[['g_code', 's_code', 'description', 'budget', 'actual_cost_ac', 'budget_balance_ac', 'variance_pct']].style.format({
            "budget": "{:,.2f}", "actual_cost_ac": "{:,.2f}", "budget_balance_ac": "{:,.2f}", "variance_pct": "{:.2f}%"
        }), use_container_width=True)
        st.markdown("""
        **ข้อมูลเชิงลึก**:
        - **CEO**: หมวดงานที่มี variance ติดลบมากอาจต้องตรวจสอบเพิ่มเติม
        - **CFO**: หมวดงานที่มี budget_balance_ac ต่ำอาจมีความเสี่ยงด้านเงินสด
        - **PM**: เปรียบเทียบประสิทธิภาพหมวดงานเพื่อปรับปรุงการบริหาร
        """)

# Footer
st.markdown("---")
st.markdown("พัฒนาโดยทีมวิเคราะห์ข้อมูลโครงการก่อสร้าง | ข้อมูลอัปเดตล่าสุด: 30 กรกฎาคม 2568")
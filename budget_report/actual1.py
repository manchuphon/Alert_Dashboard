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
def load_data_from_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    query = "SELECT * FROM actual_costs"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Load data
df = load_data_from_db()

# Data preprocessing
numeric_cols = [
    'boq', 'bg_overhead', 'bg_material', 'bg_labour', 'bg_subcontract', 'total_budget',
    'ac_overhead', 'ac_material', 'ac_labour', 'ac_subcontract', 'total_actual',
    'bg_balance', 'pg_submit', 'pg_certificate', 'pg_submit_balance'
]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Calculate percentage variance
df['variance_percentage'] = (df['bg_balance'] / df['total_budget'] * 100).round(2).fillna(0)

# Handle NULL values in 'to' column for treemap
df['to'] = df['to'].fillna('root')

# Create hierarchy label for treemap
df['hierarchy_label'] = df.apply(
    lambda row: f"{row['g_code']}: {row['description']}" if pd.isna(row['s_code'])
    else f"{row['g_code']}-{row['s_code']}: {row['description']}", axis=1
)

# Sidebar for analysis selection
st.sidebar.title("เมนูวิเคราะห์")
analysis_type = st.sidebar.selectbox(
    "เลือกประเภทการวิเคราะห์",
    [
        "👀 ภาพรวมต้นทุนทั้งหมด",
        "📈 เปรียบเทียบงบประมาณกับค่าใช้จริง",
        "🚨 รายการที่มีความเสี่ยงสูง",
        "💰 สถานะการเบิกเงิน",
        "🌳 การกระจายต้นทุนตามลำดับชั้น"
    ]
)

# Main title and description
st.title("📊 รายงานวิเคราะห์ต้นทุนโครงการก่อสร้าง")
st.markdown("เหมาะสำหรับผู้บริหาร (CEO, CFO, PM) เพื่อประเมินความคุ้มค่าและความเสี่ยงของโครงการก่อสร้าง")

# Analysis Sections
if analysis_type == "👀 ภาพรวมต้นทุนทั้งหมด":
    st.subheader("🔍 ภาพรวมต้นทุนทั้งหมด")
    
    # Summary Metrics
    total_budget = df['total_budget'].sum()
    total_actual = df['total_actual'].sum()
    total_balance = df['bg_balance'].sum()
    total_submit = df['pg_submit'].sum()
    total_certificate = df['pg_certificate'].sum()
    total_uncertified = df['pg_submit_balance'].sum()
    variance_pct = (total_balance / total_budget * 100) if total_budget > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 งบประมาณรวม", f"฿{total_budget:,.2f}")
    col2.metric("💸 ค่าใช้จ่ายจริงรวม", f"฿{total_actual:,.2f}")
    col3.metric("✅ งบคงเหลือ", f"฿{total_balance:,.2f}", delta="Positive" if total_balance > 0 else "Negative")

    col4, col5, col6 = st.columns(3)
    col4.metric("🧾 ยอดเบิกเงินทั้งหมด", f"฿{total_submit:,.2f}")
    col5.metric("📜 ยอดที่รับรองแล้ว", f"฿{total_certificate:,.2f}")
    col6.metric("⏳ ยอดรอรับรอง", f"฿{total_uncertified:,.2f}")

    # Pie Chart: Cost Structure
    pie_df = pd.DataFrame({
        "ประเภท": ["ค่าใช้จริง", "งบคงเหลือ"],
        "จำนวนเงิน": [total_actual, total_balance if total_balance > 0 else 0]
    })
    fig_pie = px.pie(pie_df, names="ประเภท", values="จำนวนเงิน", title="โครงสร้างการใช้จ่าย",
                     color_discrete_sequence=['#ff7f0e', '#2ca02c'])
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CEO**: ภาพรวมนี้แสดงถึงสุขภาพทางการเงินของโครงการ งบคงเหลือบ่งชี้ถึงความสามารถในการบริหารจัดการทรัพยากร
    - **CFO**: ยอดรอรับรองสูงอาจบ่งบอกถึงความล่าช้าในการรับเงิน ควรตรวจสอบสัญญาและกระบวนการรับรอง
    - **PM**: เปรียบเทียบค่าใช้จริงกับงบประมาณเพื่อวางแผนการใช้จ่ายในระยะต่อไป
    """)

elif analysis_type == "📈 เปรียบเทียบงบประมาณกับค่าใช้จริง":
    st.subheader("📊 เปรียบเทียบงบประมาณกับค่าใช้จริง")

    # Category Comparison
    categories = {
        "ค่าโสหุ้ย": ("bg_overhead", "ac_overhead"),
        "ค่าวัสดุ": ("bg_material", "ac_material"),
        "ค่าแรงงาน": ("bg_labour", "ac_labour"),
        "ค่าผู้รับเหมาช่วง": ("bg_subcontract", "ac_subcontract")
    }

    comparison = []
    for name, (bg_col, ac_col) in categories.items():
        bg = df[bg_col].sum()
        ac = df[ac_col].sum()
        comparison.append({
            "หมวดค่าใช้จ่าย": name,
            "งบประมาณ": bg,
            "ค่าใช้จริง": ac,
            "ส่วนต่าง": bg - ac
        })

    comp_df = pd.DataFrame(comparison)
    st.dataframe(comp_df.style.format({"งบประมาณ": "{:,.2f}", "ค่าใช้จริง": "{:,.2f}", "ส่วนต่าง": "{:,.2f}"}))

    # Bar Chart: Cost Category Comparison
    bar_df = comp_df.melt(id_vars="หมวดค่าใช้จ่าย", value_vars=["งบประมาณ", "ค่าใช้จริง"], 
                          var_name="ประเภท", value_name="จำนวน")
    fig_bar = px.bar(bar_df, x="หมวดค่าใช้จ่าย", y="จำนวน", color="ประเภท", barmode="group",
                     title="เปรียบเทียบงบประมาณกับค่าใช้จริงตามหมวด",
                     color_discrete_sequence=['#1f77b4', '#ff7f0e'])
    st.plotly_chart(fig_bar, use_container_width=True)

    # Pie Charts: Budget and Actual Breakdown
    breakdown_df = pd.DataFrame({
        'หมวด': ['ค่าโสหุ้ย', 'ค่าวัสดุ', 'ค่าแรงงาน', 'ค่าผู้รับเหมาช่วง'],
        'งบประมาณ': [df[bg_col].sum() for _, bg_col in categories.values()],
        'ค่าใช้จริง': [df[ac_col].sum() for _, ac_col in categories.values()]
    })

    col1, col2 = st.columns(2)
    fig_pie_budget = px.pie(breakdown_df, values='งบประมาณ', names='หมวด', title="โครงสร้างงบประมาณ",
                            color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
    fig_pie_actual = px.pie(breakdown_df, values='ค่าใช้จริง', names='หมวด', title="โครงสร้างค่าใช้จริง",
                            color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'])
    col1.plotly_chart(fig_pie_budget, use_container_width=True)
    col2.plotly_chart(fig_pie_actual, use_container_width=True)

    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CEO**: การเปรียบเทียบนี้แสดงถึงประสิทธิภาพการจัดการงบประมาณในแต่ละหมวด
    - **CFO**: ส่วนต่างในหมวดค่าวัสดุหรือผู้รับเหมาช่วงอาจบ่งบอกถึงโอกาสในการเจรจาราคาหรือควบคุมต้นทุน
    - **PM**: หมวดที่มีส่วนต่างมาก (เช่น ค่าแรงงาน) อาจต้องตรวจสอบการบริหารแรงงานหรือตารางงาน
    """)

elif analysis_type == "🚨 รายการที่มีความเสี่ยงสูง":
    st.subheader("⚠️ รายการที่มีความเสี่ยงสูง")

    # High-Risk Items: Negative balance or high uncertified payments
    risk_df = df[(df['bg_balance'] < 0) | (df['pg_submit_balance'] > 1000000)].copy()
    risk_df = risk_df[['g_code', 's_code', 'description', 'total_budget', 'total_actual', 
                       'bg_balance', 'variance_percentage', 'pg_submit_balance']]
    risk_df['variance_percentage'] = risk_df['variance_percentage'].apply(lambda x: f"{x:.2f}%")

    if risk_df.empty:
        st.success("✅ ไม่มีรายการที่มีความเสี่ยงสูง")
    else:
        st.warning(f"พบ {len(risk_df)} รายการที่มีความเสี่ยงสูง")
        st.dataframe(risk_df.style.format({
            "total_budget": "{:,.2f}", "total_actual": "{:,.2f}", 
            "bg_balance": "{:,.2f}", "pg_submit_balance": "{:,.2f}"
        }), use_container_width=True)

        # Top 10 Over-Budget Items
        over_budget = df[df['bg_balance'] < 0].copy()
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
    - **CEO**: รายการที่มีความเสี่ยงสูงต้องได้รับการตรวจสอบเพื่อลดผลกระทบต่อกำไรภาพรวม
    - **CFO**: รายการที่มี pg_submit_balance สูงอาจบ่งบอกถึงปัญหาการเงินสด ควรเร่งเจรจากับผู้ว่าจ้าง
    - **PM**: รายการที่เกินงบ (เช่น คอนกรีตหยาบ) อาจต้องปรับแผนงานหรือควบคุมการใช้วัสดุ
    """)

elif analysis_type == "💰 สถานะการเบิกเงิน":
    st.subheader("💰 สถานะการเบิกเงินและรับรอง")

    payment_df = df[df['pg_submit'] > 0][['g_code', 's_code', 'description', 'pg_submit', 'pg_certificate']].copy()
    payment_df['certification_rate'] = (payment_df['pg_certificate'] / payment_df['pg_submit'] * 100).round(2)

    # Bar Chart: Payment Status
    fig_payment = px.bar(
        payment_df, x='description', y=['pg_submit', 'pg_certificate'],
        title="การเบิกเงินและรับรองตามรายการ",
        barmode='group', labels={'value': 'จำนวนเงิน (บาท)', 'description': 'รายการ'},
        color_discrete_map={'pg_submit': '#1f77b4', 'pg_certificate': '#ff7f0e'}
    )
    st.plotly_chart(fig_payment, use_container_width=True)

    # Line Chart: Certification Progress
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=payment_df['description'], y=payment_df['pg_submit'], name="ยอดเบิก",
        mode='lines+markers', line=dict(color='#1f77b4')
    ))
    fig_line.add_trace(go.Scatter(
        x=payment_df['description'], y=payment_df['pg_certificate'], name="ยอดรับรอง",
        mode='lines+markers', line=dict(color='#ff7f0e')
    ))
    fig_line.update_layout(
        title="ความคืบหน้าการรับรองการเบิกเงิน",
        xaxis_title="รายการ", yaxis_title="จำนวนเงิน (บาท)",
        template='plotly_white'
    )
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CEO**: การรับรองที่ล่าช้าอาจส่งผลต่อความน่าเชื่อถือของโครงการ
    - **CFO**: ควรติดตามยอดรอรับรองเพื่อให้มั่นใจว่าเงินสดเพียงพอสำหรับดำเนินงาน
    - **PM**: ตรวจสอบรายการที่มีอัตราการรับรองต่ำเพื่อแก้ไขปัญหาการส่งมอบงาน
    """)

elif analysis_type == "🌳 การกระจายต้นทุนตามลำดับชั้น":
    st.subheader("🌳 การกระจายต้นทุนตามลำดับชั้น")

    # Treemap: Hierarchical Cost Distribution
    treemap_df = df[df['total_actual'] > 0].copy()
    fig_treemap = px.treemap(
        treemap_df, path=['to', 'g_code', 'hierarchy_label'], values='total_actual',
        title="การกระจายต้นทุนจริงตามลำดับชั้น",
        color='bg_balance', color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0
    )
    fig_treemap.update_layout(margin=dict(t=50, l=25, r=25, b=25))
    st.plotly_chart(fig_treemap, use_container_width=True)

    st.markdown("""
    **ข้อมูลเชิงลึก**:
    - **CEO**: ภาพรวมนี้แสดงถึงการกระจายต้นทุนในหมวดงานหลักและงานย่อย
    - **CFO**: ใช้เพื่อประเมินการจัดสรรงบประมาณในหมวดที่มีต้นทุนสูง (เช่น งานคอนกรีต)
    - **PM**: หมวดงานที่มี bg_balance ติดลบ (สีแดง) ต้องได้รับการตรวจสอบทันที
    """)

# Additional Filter
st.sidebar.markdown("---")
st.sidebar.subheader("ตัวกรองเพิ่มเติม")
category_filter = st.sidebar.multiselect(
    "เลือกหมวดงาน (g_code)",
    options=df['g_code'].unique(),
    default=df['g_code'].unique()
)
if category_filter:
    df = df[df['g_code'].isin(category_filter)]

# Footer
st.markdown("---")
st.markdown("พัฒนาโดยทีมวิเคราะห์ข้อมูลโครงการก่อสร้าง | ข้อมูลอัปเดตล่าสุด: 29 กรกฎาคม 2568")
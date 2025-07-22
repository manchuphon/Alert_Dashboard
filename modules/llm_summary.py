'''import google.generativeai as genai
import pandas as pd

def generate_project_summary(project_info, kpis, anomalies, vendor_forecast, gemini_api_key):
    genai.configure(api_key=gemini_api_key)

    model = genai.GenerativeModel("gemini-pro")

    # สร้าง prompt
    prompt = f"""
โครงการ: {project_info['project_name']}
งบประมาณ: {project_info['total_budget']} บาท
ความคืบหน้า: {project_info['progress_percentage']}%
ความเสี่ยง: {project_info['risk_level']}

KPI:
- CPI: {kpis['CPI']}
- SPI: {kpis['SPI']}
- BCWP: {kpis['BCWP']}
- ACWP: {kpis['ACWP']}
- EAC: {kpis['EAC']}

Anomalies:
{anomalies.to_string(index=False)}

Vendor Forecast:
{vendor_forecast[['vendor', 'forecast']].to_string(index=False)}

โปรดสรุปสถานการณ์งบประมาณและความคืบหน้า พร้อมคำแนะนำสำหรับควบคุมงบ
"""

    response = model.generate_content(prompt)
    return response.text'''

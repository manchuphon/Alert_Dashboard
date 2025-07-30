'''
ข้อมูลที่ต้องใช้:
Feature (X)	อธิบาย 
Budget	งบตั้งต้น
Actual Cost	ที่ใช้ไปแล้ว
Progress %	งานเสร็จไปกี่ %
Planned Progress (ถ้ามี)	แผนว่า % ตอนนี้ควรอยู่ที่เท่าไหร่
วันที่วันนี้	(ใช้ดู Time Trend หรือระยะเวลา)
BCWP, ACWP (ถ้ามี)	ช่วยเรื่อง performance index

Feature (y)	
EAC = Estimated Cost at Completion
ประมาณการต้นทุนรวมทั้งโครงการ เมื่อเสร็จสิ้น
'''

import pandas as pd
import numpy as np

df = pd.read_csv('C:/Users/Japan/Alert_Dashboard/data1/progress cost - ชีต1.csv')
# แยก Month/Year เป็น Month และ Year
df[['Month', 'Year']] = df['Month/Year'].str.split(' / ', expand=True)

# แสดงผลลัพธ์การแยกคอลัมน์
print("คอลัมน์หลังแยก:")
print(df[['Month/Year', 'Month', 'Year']].head())

df.drop(columns=['Month/Year'], inplace=True)  # ลบคอลัมน์ Month/Year หลังแยกแล้ว
# แสดง DataFrame ทั้งหมดพร้อมคอลัมน์ใหม่
print("\nDataFrame ทั้งหมด:")
print(df.head())

# จากนั้นใช้ df['Date'] ได้ตามปกติ

#budget at completion งบที่ตั้งไว้สำหรับโครงการนี้
BAC_PROJECT = 230580000.00
df['BAC'] = BAC_PROJECT

# แปลง Actual cost และ progress_submit เป็นตัวเลข
df['Actual cost'] = df['Actual cost'].replace(',', '', regex=True).astype(float)
df['progress_submit'] = df['progress_submit'].replace(',', '', regex=True).astype(float)


# คำนวณ Cumulative Actual Cost (ACWP)
df['ACWP'] = df['Actual cost'].cumsum().astype(int)

# คำนวณ BCWP (Budgeted Cost of Work Performed)
#    ใช้ progress_submit เป็น BCWP รายเดือน และหาผลรวมสะสม
df['BCWP'] = df['progress_submit'].cumsum().astype(int)

# คำนวณ Progress %
#    Progress % = (BCWP สะสม / BAC) * 100
df['Progress_pct'] = (df['BCWP'] / df['BAC']) * 100
# จัดการกรณีที่ BAC เป็น 0 หรือ BCWP เป็น 0 ในช่วงเริ่มต้น
df.loc[df['BAC'] == 0, 'Progress_pct'] = 0
df.loc[(df['BCWP'] == 0) & (df['BAC'] == 0), 'Progress_pct'] = 0

# คำนวณ CPI (Cost Performance Index)
df['CPI'] = df['BCWP'] / df['ACWP']
# จัดการกรณีที่ ACWP เป็น 0 (ในช่วงแรกๆ ของโครงการ)
df.loc[df['ACWP'] == 0, 'CPI'] = 1 # ถือว่าประสิทธิภาพดี 1.0 หากยังไม่ใช้เงินจริง
df.loc[(df['ACWP'] == 0) & (df['BCWP'] == 0), 'CPI'] = 1 # หากยังไม่มีทั้งงานและเงิน


#  (Optional) เพิ่ม Features จากสูตร EAC ดั้งเดิม
# EAC if CPI remains constant
df['EAC_CPI_constant'] = df['BAC'] / df['CPI']
df.loc[df['CPI'].isin([0, np.inf, -np.inf]), 'EAC_CPI_constant'] = np.nan # จัดการหารด้วย 0 หรือค่าผิดปกติ

# EAC if past variances will not occur (BAC - BCWP = Remaining work)
df['EAC_past_variances_ignored'] = df['ACWP'] + (df['BAC'] - df['BCWP'])
# ถ้า BCWP เกิน BAC แล้ว ก็แค่ ACWP ไปเลย (เพราะงานเกินงบไปแล้ว)
df.loc[df['BCWP'] > df['BAC'], 'EAC_past_variances_ignored'] = df['ACWP']


# --- Features (X) สำหรับการทำนาย ---
features_for_ML = [
    'ACWP',               # ต้นทุนสะสมที่ใช้ไปจริง
    'BCWP',               # มูลค่าของงานที่ทำได้สะสม
    'BAC',                # งบประมาณรวมของโครงการ (ค่าคงที่)
    'Progress_pct',       # เปอร์เซ็นต์ความคืบหน้าของงาน
    'CPI',                # ดัชนีประสิทธิภาพด้านต้นทุน
    # 'Months_into_Project',# ระยะเวลาที่โครงการดำเนินมาแล้ว
    # 'EAC_CPI_constant', # อาจใช้เป็น Feature เพิ่มเติมได้ หรือใช้เป็น Baseline
    # 'EAC_past_variances_ignored', # เช่นกัน
    # 'billing_cumulative', # ถ้าเชื่อว่ามีความสัมพันธ์
    # 'forecast_income_current', # ถ้าเชื่อว่ามีความสัมพันธ์
]

# แสดงตัวอย่าง DataFrame ที่มี Features ใหม่
print("DataFrame พร้อม Features ที่สร้างขึ้น:")
print(df[['Month','Year', 'Actual cost', 'ACWP', 'progress_submit', 'BCWP', 'BAC', 'Progress_pct', 'CPI', 'EAC_CPI_constant', 'EAC_past_variances_ignored']].head())
print("\n... (ท้ายตาราง) ...")
print(df[['Month','Year', 'Actual cost', 'ACWP', 'progress_submit', 'BCWP', 'BAC', 'Progress_pct', 'CPI', 'EAC_CPI_constant', 'EAC_past_variances_ignored']].tail())



df.to_csv('C:/Users/Japan/Alert_Dashboard/data1/progress_cost_features.csv', index=False)
print("✅ บันทึกข้อมูลลงไฟล์ progress_cost_features.csv เรียบร้อยแล้ว")
# --- Target (Y): EAC (Estimated Cost at Completion)




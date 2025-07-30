import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

import pandas as pd
from xgboost import XGBRegressor
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

# โหลดข้อมูล
df = pd.read_csv('C:/Users/Japan/Alert_Dashboard/data1/progress_cost_features.csv')

print(df.info())

# # 1. พล้อตความสัมพันธ์ระหว่าง Features กับ EAC
# features = ['ACWP', 'BCWP', 'Progress_pct', 'CPI']
# target = 'EAC_CPI_constant'  # ใช้เป็น target ชั่วคราว

# fig, axes = plt.subplots(2, 2, figsize=(15, 10))
# axes = axes.flatten()

# for i, feature in enumerate(features):
#     axes[i].scatter(df[feature], df[target], alpha=0.6)
#     axes[i].set_xlabel(feature)
#     axes[i].set_ylabel('EAC')
#     axes[i].set_title(f'{feature} vs EAC')

# plt.tight_layout()
# plt.show()

# # 2. Correlation Heatmap
# plt.figure(figsize=(10, 8))
# correlation_data = df[['ACWP', 'BCWP', 'Progress_pct', 'CPI', 'EAC_CPI_constant']].corr()
# sns.heatmap(correlation_data, annot=True, cmap='coolwarm', center=0)
# plt.title('Correlation Matrix')
# plt.show()

# # 3. Time series plot - แนวโน้ม EAC ตามเวลา
# plt.figure(figsize=(12, 6))
# plt.plot(range(len(df)), df['EAC_CPI_constant'], marker='o')
# plt.xlabel('Time Period')
# plt.ylabel('EAC')
# plt.title('EAC Trend Over Time')
# plt.grid(True)
# plt.show()



#Normalize features
from sklearn.preprocessing import StandardScaler

# เตรียม features และ target
features = ['ACWP', 'BCWP', 'Progress_pct', 'CPI']
X = df[features]
# y = df['EAC_CPI_constant']  # ใช้เป็น target ชั่วคราว
y = df['EAC_past_variances_ignored']  # หรือเฉลี่ยจากหลายสูตร
# y = (df['EAC_CPI_constant'] + df['EAC_past_variances_ignored']) / 2

# Normalize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# แบ่งข้อมูล train/test
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# เทรนโมเดล
xgb = XGBRegressor()
xgb.fit(X_train, y_train)

# ทำนาย EAC
xgb_pred = xgb.predict(X_test)

# วัดประสิทธิภาพโมเดล
mae = mean_absolute_error(y_test, xgb_pred)
r2 = r2_score(y_test, xgb_pred)

print(f"📊 ประสิทธิภาพโมเดล XGBoost:")
print(f"MAE: {mae:,.2f} บาท")
print(f"R²: {r2:.4f}")

# ทำนาย EAC สำหรับทุกเดือนในชุดข้อมูล
all_predictions = xgb.predict(X_scaled)

# แสดงการทำนาย EAC ในแต่ละเดือน
print(f"\n📈 การทำนาย EAC ในแต่ละเดือน:")
for idx, (month, year, actual_eac, pred_eac) in enumerate(zip(df['Month'], df['Year'], df['EAC_CPI_constant'], all_predictions)):
    print(f"{month} {year}: EAC จริง = {actual_eac:,.0f} | EAC ทำนาย = {pred_eac:,.0f} | ต่าง = {abs(actual_eac - pred_eac):,.0f}")

# แสดง Feature Importance
importance = xgb.feature_importances_
feature_names = features

plt.figure(figsize=(10, 6))
plt.barh(feature_names, importance)
plt.xlabel('Feature Importance')
plt.title('XGBoost Feature Importance')
plt.tight_layout()
plt.show()

# พล็อต Actual vs Predicted
plt.figure(figsize=(10, 6))
plt.scatter(y_test, xgb_pred, alpha=0.7)
plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', linewidth=2)
plt.xlabel('Actual EAC')
plt.ylabel('Predicted EAC')
plt.title('Actual vs Predicted EAC')
plt.grid(True)
plt.show()


# เพิ่มระบบการแจ้งเตือนหลังจากเทรนโมเดลเสร็จ

# กำหนดเกณฑ์การแจ้งเตือน
OVERRUN_THRESHOLD_PCT = 5.0  # เกิน 5%
MIN_PROGRESS_PCT = 20.0      # งานเสร็จอย่างน้อย 20%
MAX_PROGRESS_PCT = 95.0      # งานไม่เกิน 95% (หลีกเลี่ยงการแจ้งเตือนเมื่อใกล้เสร็จ)

def check_budget_alert(bac, eac_predicted, progress_pct):
    """
    ตรวจสอบการแจ้งเตือนงบเกิน
    
    Args:
        bac: Budget at Completion (งบตั้งต้น)
        eac_predicted: Estimated Cost at Completion ที่ทำนายได้
        progress_pct: เปอร์เซ็นต์งานที่เสร็จแล้ว
    
    Returns:
        dict: ผลการตรวจสอบ
    """
    overrun_amount = eac_predicted - bac
    overrun_pct = (overrun_amount / bac) * 100 if bac > 0 else 0
    
    # เงื่อนไขการแจ้งเตือน
    should_alert = (
        overrun_pct > OVERRUN_THRESHOLD_PCT and 
        MIN_PROGRESS_PCT <= progress_pct <= MAX_PROGRESS_PCT
    )
    
    return {
        'should_alert': should_alert,
        'overrun_amount': overrun_amount,
        'overrun_pct': overrun_pct,
        'bac': bac,
        'eac_predicted': eac_predicted,
        'progress_pct': progress_pct
    }

# ทำนาย EAC สำหรับทุกเดือนและตรวจสอบการแจ้งเตือน
print(f"\n⚠️ ระบบแจ้งเตือนงบเกิน (เกณฑ์: เกิน {OVERRUN_THRESHOLD_PCT}% และงานอยู่ที่ {MIN_PROGRESS_PCT}-{MAX_PROGRESS_PCT}%):")
print("="*80)

alert_count = 0
alert_months = []  # เก็บรายชื่อเดือนที่เกินงบ

for idx, (month, year, bac, progress_pct, pred_eac) in enumerate(zip(
    df['Month'], df['Year'], df['BAC'], df['Progress_pct'], all_predictions
)):
    alert = check_budget_alert(bac, pred_eac, progress_pct)
    
    if alert['should_alert']:
        alert_count += 1
        alert_months.append(f"{month} {year}")  # เก็บชื่อเดือนที่เกิน
        
        print(f"🚨 ALERT #{alert_count} - {month} {year}:")
        print(f"   📊 งบตั้งต้น (BAC): {alert['bac']:,.0f} บาท")
        print(f"   💰 EAC ทำนาย: {alert['eac_predicted']:,.0f} บาท")
        print(f"   📈 งานเสร็จ: {alert['progress_pct']:.1f}%")
        print(f"   ⚡ เกินงบ: {alert['overrun_amount']:,.0f} บาท ({alert['overrun_pct']:.1f}%)")
        print(f"   💡 แนะนำ: ควรทบทวนแผนงานและงบประมาณ")
        print("-" * 60)

if alert_count == 0:
    print("✅ ไม่พบการแจ้งเตือน: งบประมาณทุกเดือนอยู่ในเกณฑ์ปกติ")
else:
    print(f"\n📊 สรุป: พบการแจ้งเตือน {alert_count} ครั้ง จากทั้งหมด {len(df)} เดือน")
    print(f"📅 เดือนที่เกินงบ: {', '.join(alert_months)}")
    
   
import pandas as pd
from xgboost import XGBRegressor
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

# โหลดข้อมูล
df = pd.read_csv('C:/Users/Japan/Alert_Dashboard/data1/evm_results.csv')

# สร้าง duration_days สำหรับทุกโครงการใน df
df['start_date'] = pd.to_datetime(df['start_date'])
df['end_date'] = pd.to_datetime(df['end_date'])
df['duration_days'] = (df['end_date'] - df['start_date']).dt.days

# ให้ user เลือกโครงการ
project_name = input("กรุณาใส่ชื่อโครงการที่ต้องการทำนาย: ")
project = df[df['project_name'] == project_name].iloc[0]
print("\nข้อมูลโครงการที่เลือก:")
print(project)


# เตรียม features สำหรับโมเดล
features = {
    'total_budget': project['total_budget'],
    'acwp': project['acwp'],
    'progress_percentage': project['progress_percentage'],
    'planned_progress': project['planned_progress'],
    'bcwp': project['bcwp'],
    'duration_days': project['duration_days']
}
X_new = pd.DataFrame([features])
X = df[list(features.keys())]
y = df['eac']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# แบ่งข้อมูล train/test
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
# XGBoost
xgb = XGBRegressor(
    n_estimators=200,      # จำนวนต้นไม้ (trees)
    max_depth=4,           # ความลึกสูงสุดของแต่ละต้นไม้
    learning_rate=0.1,     # อัตราการเรียนรู้        
    colsample_bytree=0.8,  # สัดส่วน feature ที่ใช้ในแต่ละต้นไม้
    random_state=42        # เพื่อ reproducibility
)
xgb.fit(X_train, y_train)
xgb_pred = xgb.predict(X_test)
# print("ผลการทำนาย EAC ด้วย XGBoost:")
# for idx, pred in zip(X_test.index, xgb_pred):
#     budget = X_test.loc[idx, 'total_budget']
#     overrun_pct = (pred - budget) / budget * 100
#     print(f"Project index {idx}: EAC ทำนาย = {pred:.2f} ({overrun_pct:.2f}%)")
# ทำนาย EAC
eac_pred = xgb.predict(X_new)[0]
overrun_pct = (eac_pred - features['total_budget']) / features['total_budget'] * 100

print(f"\nโครงการ: {project_name}")
print(f"EAC ทำนาย = {eac_pred:.2f} บาท")
print(f"เปอร์เซ็นต์งบเกิน = {overrun_pct:.2f}%")
if overrun_pct > 5:
    print("⚠️ มีแนวโน้มงบจะเกิน 5%")
else:
    print("✅ งบยังอยู่ในแผน")

# ประเมินผล XGBoost
mae = mean_absolute_error(y_test, xgb_pred)
r2 = r2_score(y_test, xgb_pred)

print(f"\nXGBoost MAE: {mae:.2f}")
print(f"XGBoost R2: {r2:.2f}")

# XGBoost (default parameter)
xgb_default = XGBRegressor()
xgb_default.fit(X_train, y_train)
xgb_default_pred = xgb_default.predict(X_test)

# ประเมินผล XGBoost (default)
mae_default = mean_absolute_error(y_test, xgb_default_pred)
r2_default = r2_score(y_test, xgb_default_pred)

print(f"\nXGBoost (default) MAE: {mae_default:.2f}")
print(f"XGBoost (default) R2: {r2_default:.2f}")

# ทำนาย EAC สำหรับโครงการที่เลือก (default)
eac_pred_default = xgb_default.predict(X_new)[0]
overrun_pct_default = (eac_pred_default - features['total_budget']) / features['total_budget'] * 100

print(f"\n[EAC Default] โครงการ: {project_name}")
print(f"EAC ทำนาย = {eac_pred_default:.2f} บาท")
print(f"เปอร์เซ็นต์งบเกิน = {overrun_pct_default:.2f}%")
if overrun_pct_default > 5:
    print("⚠️ มีแนวโน้มงบจะเกิน 5% (default)")
else:
    print("✅ งบยังอยู่ในแผน (default)")









#XGBoost (ปรับ parameter) หลังจาก cross validationแล้ว
# Cross Validation สำหรับ XGBoost (parameter ที่ปรับแล้ว)
cv_scores = cross_val_score(
    xgb, X_scaled, y, cv=10, scoring='neg_mean_absolute_error'
)
print(f"\nXGBoost (ปรับ parameter) MAE เฉลี่ยจาก CV: {-cv_scores.mean():.2f}")

# Cross Validation สำหรับ XGBoost (default parameter)
cv_scores_default = cross_val_score(
    xgb_default, X_scaled, y, cv=5, scoring='neg_mean_absolute_error'
)
print(f"XGBoost (default) MAE เฉลี่ยจาก CV: {-cv_scores_default.mean():.2f}")
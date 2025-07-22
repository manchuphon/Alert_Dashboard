import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

def load_vendor_data(vendors_csv, expenses_csv):
    vendors = pd.read_csv("/Users/aoyrzz/Downloads/ai_budget_alert_dashboard_streamlit_full/data1/vendors.csv")
    expenses = pd.read_csv("/Users/aoyrzz/Downloads/ai_budget_alert_dashboard_streamlit_full/data1/expenses.csv")

    print(f"📦 Vendors shape: {vendors.shape}")
    print(f"📦 Expenses shape: {expenses.shape}")

    # แปลงวันที่
    expenses['expense_date'] = pd.to_datetime(expenses['expense_date'], errors='coerce')
    expenses['approval_date'] = pd.to_datetime(expenses['approval_date'], errors='coerce')

    # คำนวณ delay (วันที่อนุมัติ - วันที่ใช้จ่าย)
    expenses['delay'] = (expenses['approval_date'] - expenses['expense_date']).dt.days

    # เฉลี่ย delay ต่อ vendor
    vendor_delay = expenses.groupby('vendor')['delay'].mean().reset_index()
    vendor_delay.columns = ['vendor_name', 'avg_delay']
    vendor_delay['on_time'] = vendor_delay['avg_delay'].apply(lambda d: 1 if d <= 5 else 0)

    print(f"📊 Vendor delay shape: {vendor_delay.shape}")

    # Merge กับ vendors
    df = pd.merge(vendors, vendor_delay, on='vendor_name', how='inner')
    if df.empty:
        print("❌ Merged dataframe is empty. ตรวจสอบชื่อ vendor ให้ตรงกัน")
        return df

    print(f"🔗 Merged df shape: {df.shape}")

    # เลือก features ที่จะใช้
    df = df[['rating', 'payment_terms', 'total_contracts', 'total_value', 'avg_delay', 'on_time']]
    df = pd.get_dummies(df, columns=['rating', 'payment_terms'], drop_first=True)

    return df

def train_and_save_vendor_model(df, output_path='saved_models/vendor_model.pkl'):
    if df.empty:
        print("❌ Dataframe is empty. Model training aborted.")
        return

    X = df.drop('on_time', axis=1)
    y = df['on_time']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("📋 Classification Report:\n", classification_report(y_test, y_pred))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    print(f"✅ Vendor model saved to {output_path}")

if __name__ == '__main__':
    data = load_vendor_data(
        'vendors_mock.csv',
        'expenses_mock.csv'
    )
    train_and_save_vendor_model(data)

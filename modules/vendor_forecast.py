'''import pandas as pd

def forecast_vendor_payment(vendors_df, expenses_df):
    expenses_df['expense_date'] = pd.to_datetime(expenses_df['expense_date'], errors='coerce')
    expenses_df['approval_date'] = pd.to_datetime(expenses_df['approval_date'], errors='coerce')
    expenses_df['delay'] = (expenses_df['approval_date'] - expenses_df['expense_date']).dt.days

    vendor_project_delay = expenses_df.groupby(['vendor', 'project_id'])['delay'].mean().reset_index()
    merged = pd.merge(vendor_project_delay, vendors_df, how='left', left_on='vendor', right_on='vendor_name')
    merged['forecast'] = merged.apply(lambda row: _predict(row['rating'], row['delay']), axis=1)

    return merged[['vendor', 'project_id', 'rating', 'delay', 'forecast', 'vendor_type',
                   'total_contracts', 'total_value', 'payment_terms']]

def _predict(rating, delay):
    if pd.isna(delay): return "ไม่พบข้อมูล"
    if rating == 'A' and delay <= 3:
        return 'จ่ายตรงเวลา'
    elif rating == 'B' and delay <= 7:
        return 'อาจล่าช้าเล็กน้อย'
    elif rating in ['C', 'D'] or delay > 10:
        return 'ล่าช้าบ่อย'
    return 'ความเสี่ยงสูง'''

'''import pandas as pd

def detect_anomalies(project_data):
    df = project_data['budgets'].copy()
    df['deviation'] = df['spent_amount'] - df['allocated_amount']
    df['anomaly'] = df['deviation'].apply(lambda x: "⚠️ เกินงบ" if x > 0 else "✅ ปกติ")
    return df[['category', 'allocated_amount', 'spent_amount', 'deviation', 'anomaly']]'''

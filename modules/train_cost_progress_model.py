
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

def load_training_data(projects_csv, budgets_csv):
    projects = pd.read_csv("/Users/aoyrzz/Downloads/ai_budget_alert_dashboard_streamlit_full/data1/projects.csv")
    budgets = pd.read_csv("/Users/aoyrzz/Downloads/ai_budget_alert_dashboard_streamlit_full/data1/budgets.csv")

    summary = budgets.groupby('project_id').agg({
        'allocated_amount': 'sum',
        'spent_amount': 'sum'
    }).reset_index()

    merged = pd.merge(projects, summary, on='project_id')
    merged['progress_pct'] = merged['progress_percentage']
    merged['spent_pct'] = (merged['spent_amount'] / merged['allocated_amount']) * 100

    # Label แบบง่าย: ถ้า spent เกิน progress * 1.5 = 1 (ผิดปกติ)
    merged['label'] = merged.apply(lambda x: 1 if x['spent_pct'] > x['progress_pct'] * 1.5 else 0, axis=1)

    return merged[['progress_pct', 'spent_pct', 'label']]

def train_and_save_model(data, output_path='saved_models/cost_progress_model.pkl'):
    X = data[['progress_pct', 'spent_pct']]
    y = data['label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LogisticRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred)
    print("📋 Classification Report:\n", report)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    print(f"✅ Model saved to {output_path}")

def extract_cost_progress_features(project_data):
    spent_total = project_data['budgets']['spent_amount'].sum()
    allocated_total = project_data['budgets']['allocated_amount'].sum()
    progress = project_data['projects']['progress_percentage'].iloc[0]

    spent_pct = (spent_total / allocated_total) * 100 if allocated_total else 0

    return round(progress, 2), round(spent_pct, 2)


if __name__ == '__main__':
    data = load_training_data('/Users/aoyrzz/Downloads/ai_budget_alert_dashboard_streamlit_full/data1/projects.csv', '/Users/aoyrzz/Downloads/ai_budget_alert_dashboard_streamlit_full/data1/budgets.csv')
    train_and_save_model(data)

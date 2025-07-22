import pandas as pd
import os

def load_all_data(data_dir):
    return {
        "projects": pd.read_csv(os.path.join(data_dir, "projects.csv")),
        "budgets": pd.read_csv(os.path.join(data_dir, "budgets.csv")),
        "expenses": pd.read_csv(os.path.join(data_dir, "expenses.csv")),
        "resources": pd.read_csv(os.path.join(data_dir, "resources.csv")),
        "vendors": pd.read_csv(os.path.join(data_dir, "vendors.csv")),
        "milestones": pd.read_csv(os.path.join(data_dir, "milestones.csv")),
        "change_requests": pd.read_csv(os.path.join(data_dir, "change_requests.csv")),
        "risks": pd.read_csv(os.path.join(data_dir, "risks.csv"))
    }

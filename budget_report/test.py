import pandas as pd
import os
import matplotlib.pyplot as plt

#-----------------------------#
#       Load and Clean Data  #
#-----------------------------#

def load_data(filename, file_path='data1'):
    """Load CSV file, skip metadata rows, and clean up unnecessary columns."""
    full_path = os.path.join(file_path, filename)
    df = pd.read_csv(full_path, skiprows=3)
    df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]  # Drop unnamed columns
    df = df[df['G-Code'].notna()]  # Keep rows with valid G-Code
    return df.reset_index(drop=True)

def clean_numeric_columns(df, columns):
    """Convert number-like strings to float (remove commas)."""
    for col in columns:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False).astype(float)
    return df

#-----------------------------#
#     Perspective 1: Basic % Used
#-----------------------------#

def analyze_percent_used(df):
    """Analyze and plot top 10 G-Codes by percentage of budget used."""
    numeric_cols = [
        'Total Budget', 'Total Actual', 'BG Overhead', 'BG Material', 'BG Labour',
        'BG Subc.', 'AC Overhead', 'AC Material', 'AC Labour', 'AC Subc.', 'BG Balance'
    ]
    df = clean_numeric_columns(df, numeric_cols)
    df['Percent Used'] = (df['Total Actual'] / df['Total Budget']) * 100

    top_used = df[['G-Code', 'Description', 'Total Budget', 'Total Actual', 'Percent Used']]
    top_used = top_used.sort_values(by='Percent Used', ascending=False)

    # Show top 10 in terminal
    print("\n[Perspective 1] Top 10 G-Codes by % Used:")
    print(top_used.head(10))

    # Plot
    top10 = top_used.head(10)
    plt.figure(figsize=(12,6))
    bar_width = 0.35
    index = range(len(top10))

    plt.bar(index, top10['Total Budget'], bar_width, label='Budget')
    plt.bar([i + bar_width for i in index], top10['Total Actual'], bar_width, label='Actual')

    plt.xticks([i + bar_width / 2 for i in index], top10['G-Code'], rotation=45)
    plt.xlabel('G-Code')
    plt.ylabel('Amount (THB)')
    plt.title('Top 10 G-Codes by Budget vs Actual Spend')
    plt.legend()
    plt.tight_layout()
    plt.show()

#-----------------------------#
#     Perspective 2: Budget Difference
#-----------------------------#

def analyze_budget_difference(df):
    """Analyze and plot top 10 G-Codes by actual usage % and budget difference."""
    df['Total Budget'] = df['Total Budget'].astype(str).str.replace(',', '').astype(float)
    df['Total Actual'] = df['Total Actual'].astype(str).str.replace(',', '').astype(float)

    df['Budget Diff'] = df['Total Budget'] - df['Total Actual']
    df['Actual Usage (%)'] = (df['Total Actual'] / df['Total Budget']) * 100

    summary = df[['G-Code', 'Description', 'Total Budget', 'Total Actual', 'Budget Diff', 'Actual Usage (%)']]
    summary = summary.sort_values(by='Actual Usage (%)', ascending=False)

    # Show top 10 in terminal
    print("\n[Perspective 2] Top 10 G-Codes by Actual Usage % and Budget Diff:")
    print(summary.head(10))

    # Plot
    plot_data = summary.head(10)
    plt.figure(figsize=(12,6))
    plt.bar(plot_data['G-Code'], plot_data['Actual Usage (%)'], color='skyblue')
    plt.axhline(100, color='red', linestyle='--', label='100% Budget Used')
    plt.title('Top 10 G-Codes: % of Budget Used')
    plt.ylabel('% Used')
    plt.xlabel('G-Code')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()

#-----------------------------#
#            Main
#-----------------------------#

if __name__ == "__main__":
    actual_cost_df = load_data("Actual_Cost.csv")
    
    # Perspective 1: Percent of budget used
    analyze_percent_used(actual_cost_df.copy())

    # Perspective 2: Budget vs Actual + Diff
    analyze_budget_difference(actual_cost_df.copy())

print("Actual_Cost.csv G-Codes:", actual_cost_df['G-Code'].nunique())
# print("Summary_Cost.csv G-Codes:", df_summary['G-Code'].nunique())

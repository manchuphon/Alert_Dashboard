'''def calculate_kpis(project_data):
    bcwp = project_data['milestones']['budget_allocated'].sum()
    acwp = project_data['milestones']['budget_spent'].sum()
    pv = project_data['budgets']['allocated_amount'].sum()
    bac = project_data['projects']['total_budget'].iloc[0]

    cpi = bcwp / acwp if acwp != 0 else None
    spi = bcwp / pv if pv != 0 else None
    eac = bac / cpi if cpi else None

    return {
        "BCWP": bcwp,
        "ACWP": acwp,
        "CPI": round(cpi, 2) if cpi else None,
        "SPI": round(spi, 2) if spi else None,
        "EAC": round(eac, 2) if eac else None
    }'''

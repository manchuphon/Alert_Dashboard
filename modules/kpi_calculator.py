import pandas as pd
import numpy as np
from datetime import datetime

def calculate_evm_metrics(projects_csv, budgets_csv, expenses_csv, resources_csv, vendors_csv, milestones_csv):
    """
    คำนวณค่า CPI, SPI, BCWP, ACWP, EAC จากไฟล์ CSV
    
    Parameters:
    -----------
    projects_csv : str - path ไฟล์ projects.csv
    budgets_csv : str - path ไฟล์ budgets.csv  
    expenses_csv : str - path ไฟล์ expenses.csv
    resources_csv : str - path ไฟล์ resources.csv
    vendors_csv : str - path ไฟล์ vendors.csv
    milestones_csv : str - path ไฟล์ milestones.csv
    
    Returns:
    --------
    pandas.DataFrame - ผลลัพธ์การคำนวณ EVM metrics สำหรับทุกโครงการ
    """
    
    # โหลดข้อมูล
    try:
        projects_df = pd.read_csv(projects_csv)
        budgets_df = pd.read_csv(budgets_csv)
        expenses_df = pd.read_csv(expenses_csv)
        resources_df = pd.read_csv(resources_csv)
        vendors_df = pd.read_csv(vendors_csv)
        milestones_df = pd.read_csv(milestones_csv)
        
        print("✅ โหลดข้อมูลสำเร็จ")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการโหลดไฟล์: {e}")
        return None
    
    # แปลงข้อมูลวันที่
    try:
        projects_df['start_date'] = pd.to_datetime(projects_df['start_date'], errors='coerce')
        projects_df['end_date'] = pd.to_datetime(projects_df['end_date'], errors='coerce')
        expenses_df['expense_date'] = pd.to_datetime(expenses_df['expense_date'], errors='coerce')
        milestones_df['planned_date'] = pd.to_datetime(milestones_df['planned_date'], errors='coerce')
        milestones_df['actual_date'] = pd.to_datetime(milestones_df['actual_date'], errors='coerce')
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาดในการแปลงวันที่: {e}")
    
    # คำนวณ EVM metrics
    results = []
    current_date = datetime.now()
    
    print(f"📊 กำลังคำนวณ EVM metrics สำหรับ {len(projects_df)} โครงการ...")
    
    for index, project in projects_df.iterrows():
        project_id = project['project_id']
        project_name = project['project_name']
        total_budget = project['total_budget']
        progress_percentage = project['progress_percentage']
        start_date = project['start_date']
        end_date = project['end_date']
        
        # ตรวจสอบข้อมูลพื้นฐาน
        if pd.isna(total_budget) or pd.isna(progress_percentage):
            print(f"⚠️ ข้อมูลไม่ครบสำหรับโครงการ {project_id} - {project_name}")
            continue
        
        # ===========================================
        # 1. คำนวณ BCWP (Budgeted Cost of Work Performed)
        # ===========================================
        # BCWP = Earned Value = งบประมาณรวม × เปอร์เซ็นต์ความคืบหน้าจริง
        bcwp = total_budget * (progress_percentage / 100)
        
        # ===========================================  
        # 2. คำนวณ ACWP (Actual Cost of Work Performed)
        # ===========================================
        # ACWP = ยอดรวมค่าใช้จ่ายจริงทั้งหมดของโครงการ
        project_expenses = expenses_df[expenses_df['project_id'] == project_id]
        acwp = project_expenses['amount'].sum() if not project_expenses.empty else 0
        
        # ===========================================
        # 3. คำนวณ BCWS (Budgeted Cost of Work Scheduled)  
        # ===========================================
        # BCWS = Planned Value = งบประมาณที่ควรจะใช้ตามแผน
        if pd.notna(start_date) and pd.notna(end_date):
            total_days = (end_date - start_date).days
            elapsed_days = (current_date - start_date).days
            
            if total_days > 0:
                # คำนวณเปอร์เซ็นต์ความคืบหน้าตามแผน
                planned_progress = min(100, max(0, (elapsed_days / total_days) * 100))
            else:
                planned_progress = 0
        else:
            # หากไม่มีข้อมูลวันที่ ใช้ความคืบหน้าปัจจุบัน
            planned_progress = progress_percentage
        
        bcws = total_budget * (planned_progress / 100)
        
        # ===========================================
        # 4. คำนวณ CPI (Cost Performance Index)
        # ===========================================
        # CPI = BCWP / ACWP 
        # ค่ามากกว่า 1 = ใช้งบน้อยกว่าแผน, น้อยกว่า 1 = ใช้งบเกินแผน
        if acwp > 0:
            cpi = bcwp / acwp
        else:
            cpi = float('inf') if bcwp > 0 else 1.0  # ถ้าไม่มีค่าใช้จ่าย
        
        # ===========================================
        # 5. คำนวณ SPI (Schedule Performance Index)
        # ===========================================  
        # SPI = BCWP / BCWS
        # ค่ามากกว่า 1 = เร็วกว่าแผน, น้อยกว่า 1 = ช้ากว่าแผน
        if bcws > 0:
            spi = bcwp / bcws
        else:
            spi = float('inf') if bcwp > 0 else 1.0  # ถ้าไม่มี planned value
        
        # ===========================================
        # 6. คำนวณ Cost Variance (CV) และ Schedule Variance (SV)
        # ===========================================
        cost_variance = bcwp - acwp        # CV > 0 = ประหยัดงบ, CV < 0 = เกินงบ
        schedule_variance = bcwp - bcws     # SV > 0 = เร็วกว่าแผน, SV < 0 = ช้ากว่าแผน
        
        # ===========================================
        # 7. คำนวณ EAC (Estimate at Completion)
        # ===========================================
        # EAC = ACWP + (BAC - BCWP) / CPI
        # ประมาณการต้นทุนรวมที่จะเกิดขึ้นเมื่องานเสร็จ
        if cpi > 0 and not np.isinf(cpi):
            work_remaining = total_budget - bcwp  # งานที่เหลือ
            eac = acwp + (work_remaining / cpi)
        else:
            eac = total_budget  # ใช้งบประมาณเดิมหาก CPI ไม่สามารถคำนวณได้
        
        # ===========================================
        # 8. คำนวณค่าเพิ่มเติม
        # ===========================================
        
        # Variance at Completion (VAC)
        vac = total_budget - eac
        
        # To Complete Performance Index (TCPI)
        work_remaining = total_budget - bcwp
        budget_remaining = total_budget - acwp
        
        if budget_remaining > 0:
            tcpi = work_remaining / budget_remaining
        else:
            tcpi = float('inf') if work_remaining > 0 else 0
        
        # Percent Complete
        percent_complete = progress_percentage
        
        # Percent Spent  
        percent_spent = (acwp / total_budget * 100) if total_budget > 0 else 0
        
        # ===========================================
        # 9. ประเมินสถานะและความเสี่ยง
        # ===========================================
        
        # ประเมินสถานะโครงการ
        if np.isinf(cpi) or np.isinf(spi):
            status = "ข้อมูลไม่เพียงพอ"
            performance_status = "Unknown"
        elif cpi >= 1.0 and spi >= 1.0:
            status = "ดีเยี่ยม"
            performance_status = "On Track"
        elif cpi >= 0.9 and spi >= 0.9:
            status = "ปกติ"
            performance_status = "Minor Issues"
        elif cpi >= 0.8 or spi >= 0.8:
            status = "เฝ้าระวัง"
            performance_status = "At Risk"
        else:
            status = "มีปัญหา"
            performance_status = "Critical"
        
        # ประเมินระดับความเสี่ยง
        risk_score = 0
        
        if not np.isinf(cpi):
            if cpi < 0.8:
                risk_score += 3
            elif cpi < 0.9:
                risk_score += 2
            elif cpi < 1.0:
                risk_score += 1
        
        if not np.isinf(spi):
            if spi < 0.8:
                risk_score += 3
            elif spi < 0.9:
                risk_score += 2
            elif spi < 1.0:
                risk_score += 1
        
        # ประเมินจาก Cost Variance
        if abs(cost_variance) > total_budget * 0.2:
            risk_score += 2
        elif abs(cost_variance) > total_budget * 0.1:
            risk_score += 1
        
        if risk_score >= 5:
            risk_level = "สูง"
        elif risk_score >= 3:
            risk_level = "ปานกลาง"
        else:
            risk_level = "ต่ำ"
        
        # ===========================================
        # 10. เก็บผลลัพธ์
        # ===========================================
        result = {
            'project_id': project_id,
            'project_name': project_name,
            'project_type': project.get('project_type', 'N/A'),
            'client': project.get('client', 'N/A'),
            'project_manager': project.get('project_manager', 'N/A'),
            'total_budget': total_budget,
            'progress_percentage': progress_percentage,
            'planned_progress': planned_progress,
            
            # Core EVM Metrics
            'bcwp': bcwp,                    # Budgeted Cost of Work Performed (Earned Value)
            'acwp': acwp,                    # Actual Cost of Work Performed
            'bcws': bcws,                    # Budgeted Cost of Work Scheduled (Planned Value)
            'cpi': cpi,                      # Cost Performance Index
            'spi': spi,                      # Schedule Performance Index
            'eac': eac,                      # Estimate at Completion
            
            # Additional Metrics
            'vac': vac,                      # Variance at Completion
            'tcpi': tcpi,                    # To Complete Performance Index
            'cost_variance': cost_variance,   # Cost Variance (CV)
            'schedule_variance': schedule_variance,  # Schedule Variance (SV)
            'percent_complete': percent_complete,
            'percent_spent': percent_spent,
            
            # Status and Risk
            'status': status,
            'performance_status': performance_status,
            'risk_level': risk_level,
            'risk_score': risk_score,
            
            # Dates
            'start_date': start_date,
            'end_date': end_date,
            'calculation_date': current_date
        }
        
        results.append(result)
        
        # แสดง progress
        if (index + 1) % 10 == 0:
            print(f"   คำนวณแล้ว {index + 1}/{len(projects_df)} โครงการ")
    
    # สร้าง DataFrame จากผลลัพธ์
    evm_df = pd.DataFrame(results)
    
    print(f"✅ คำนวณเสร็จสิ้น {len(evm_df)} โครงการ")
    
    return evm_df

def print_evm_summary(evm_df):
    """แสดงสรุปผลการคำนวณ EVM"""
    
    if evm_df is None or evm_df.empty:
        print("❌ ไม่มีข้อมูลสำหรับแสดงสรุป")
        return
    
    print("\n" + "="*80)
    print("📊 สรุปผลการคำนวณ Earned Value Management")
    print("="*80)
    
    # สถิติพื้นฐาน
    total_projects = len(evm_df)
    total_budget = evm_df['total_budget'].sum()
    total_acwp = evm_df['acwp'].sum()
    total_bcwp = evm_df['bcwp'].sum()
    
    # CPI และ SPI โดยรวม
    overall_cpi = total_bcwp / total_acwp if total_acwp > 0 else 0
    overall_spi = evm_df['spi'].replace([np.inf, -np.inf], np.nan).mean()
    
    print(f"\n🎯 สถิติโดยรวม:")
    print(f"   จำนวนโครงการ: {total_projects:,} โครงการ")
    print(f"   งบประมาณรวม: {total_budget:,.0f} บาท")
    print(f"   ค่าใช้จ่ายจริงรวม: {total_acwp:,.0f} บาท")
    print(f"   Earned Value รวม: {total_bcwp:,.0f} บาท")
    print(f"   CPI โดยรวม: {overall_cpi:.3f}")
    print(f"   SPI เฉลี่ย: {overall_spi:.3f}")
    print(f"   ความคืบหน้าเฉลี่ย: {evm_df['progress_percentage'].mean():.1f}%")
    
    # การกระจายของสถานะ
    status_counts = evm_df['status'].value_counts()
    print(f"\n📈 สถานะโครงการ:")
    for status, count in status_counts.items():
        percentage = count / total_projects * 100
        print(f"   {status}: {count} โครงการ ({percentage:.1f}%)")
    
    # การกระจายของความเสี่ยง
    risk_counts = evm_df['risk_level'].value_counts()
    print(f"\n⚠️ ระดับความเสี่ยง:")
    for risk, count in risk_counts.items():
        percentage = count / total_projects * 100
        print(f"   ความเสี่ยง{risk}: {count} โครงการ ({percentage:.1f}%)")
    
    # โครงการที่มีปัญหา
    problem_projects = evm_df[
        (evm_df['cpi'] < 0.9) | (evm_df['spi'] < 0.9)
    ]
    
    if not problem_projects.empty:
        print(f"\n🚨 โครงการที่ต้องเฝ้าระวัง ({len(problem_projects)} โครงการ):")
        for _, project in problem_projects.head(5).iterrows():
            cpi_str = f"{project['cpi']:.2f}" if not np.isinf(project['cpi']) else "∞"
            spi_str = f"{project['spi']:.2f}" if not np.isinf(project['spi']) else "∞"
            print(f"   • {project['project_name']} (CPI: {cpi_str}, SPI: {spi_str})")
    
    print("="*80)

def export_evm_results(evm_df, output_file='evm_results.csv'):
    """ส่งออกผลลัพธ์เป็นไฟล์ CSV"""
    
    if evm_df is None or evm_df.empty:
        print("❌ ไม่มีข้อมูลสำหรับส่งออก")
        return False
    
    try:
        # เตรียมข้อมูลสำหรับส่งออก
        export_df = evm_df.copy()
        
        # แปลงค่า infinity เป็น string
        export_df['cpi'] = export_df['cpi'].replace([np.inf, -np.inf], 'Infinity')
        export_df['spi'] = export_df['spi'].replace([np.inf, -np.inf], 'Infinity')
        export_df['eac'] = export_df['eac'].replace([np.inf, -np.inf], 'Infinity')
        export_df['tcpi'] = export_df['tcpi'].replace([np.inf, -np.inf], 'Infinity')
        
        # ส่งออกไฟล์
        export_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ ส่งออกผลลัพธ์สำเร็จ: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งออก: {e}")
        return False

# ตัวอย่างการใช้งาน
if __name__ == "__main__":
    print("🚀 เริ่มต้นการคำนวณ EVM Metrics")
    print("="*50)
    
    # กำหนด path ไฟล์ CSV
    file_paths = {
        'projects_csv': 'data1/projects.csv',
        'budgets_csv': 'data1/budgets.csv',
        'expenses_csv': 'data1/expenses.csv', 
        'resources_csv': 'data1/resources.csv',
        'vendors_csv': 'data1/vendors.csv',
        'milestones_csv': 'data1/milestones.csv'
    }
# ...existing code...
    # คำนวณ EVM metrics
    results = calculate_evm_metrics(**file_paths)
    
    if results is not None:
        # แสดงสรุปผลลัพธ์
        print_evm_summary(results)
        
        # แสดงตัวอย่างข้อมูล 5 โครงการแรก
        print(f"\n📋 ตัวอย่างผลลัพธ์ (5 โครงการแรก):")
        print("-"*120)
        cols_to_show = ['project_name', 'total_budget', 'progress_percentage', 
                       'bcwp', 'acwp', 'cpi', 'spi', 'eac', 'status']
        
        sample_df = results[cols_to_show].head()
        for col in ['total_budget', 'bcwp', 'acwp', 'eac']:
            sample_df[col] = sample_df[col].apply(lambda x: f"{x:,.0f}")
        for col in ['cpi', 'spi']:
            sample_df[col] = sample_df[col].apply(lambda x: f"{x:.3f}" if not np.isinf(x) else "∞")
        
        print(sample_df.to_string(index=False))
        
        # ส่งออกผลลัพธ์
        export_evm_results(results)
        
        print(f"\n✅ การคำนวณเสร็จสิ้น! ตรวจสอบไฟล์ evm_results.csv สำหรับผลลัพธ์ทั้งหมด")
    
    else:
        print("❌ การคำนวณล้มเหลว กรุณาตรวจสอบไฟล์ข้อมูล")
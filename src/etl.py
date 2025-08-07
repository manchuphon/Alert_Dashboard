"""
ETL Script สำหรับ AI Budget Alert Dashboard
รวมข้อมูลจาก ERP เป็น Master Schema สำหรับ ML
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings('ignore')

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_log.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BudgetETL:
    """
    ETL Pipeline สำหรับ AI Budget Alert Dashboard
    """
    
    def __init__(self, data_dir='data/raw/', output_dir='data/processed/'):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.create_output_dir()
        
        # ตั้งค่าไฟล์ input
        self.files = {
            'actual_cost': '/Users/aoyrzz/Desktop/Alert_Dashboard3/data/actual_cost_data.csv',
            'summary_cost': '/Users/aoyrzz/Desktop/Alert_Dashboard3/data/summary_cost_data.csv',
            'progress_payment': '/Users/aoyrzz/Desktop/Alert_Dashboard3/data/progress_payment_data.csv',
            'projects_master': '/Users/aoyrzz/Desktop/Alert_Dashboard3/data/projects_master.csv',
            'cost_codes_master': '/Users/aoyrzz/Desktop/Alert_Dashboard3/data/cost_codes_master.csv'
        }
        
        # เก็บ dataframes
        self.dataframes = {}
        self.master_data = None
        
    def create_output_dir(self):
        """สร้าง directory สำหรับ output"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(f"{self.output_dir}/quality_reports/", exist_ok=True)
        
    def load_data(self):
        """
        โหลดข้อมูลจากไฟล์ CSV ทั้งหมด
        """
        logger.info("🔄 เริ่มโหลดข้อมูล...")
        
        for key, filename in self.files.items():
            filepath = os.path.join(self.data_dir, filename)
            
            try:
                # อ่านไฟล์ CSV
                df = pd.read_csv(filepath, encoding='utf-8-sig')
                self.dataframes[key] = df
                logger.info(f"✅ โหลด {filename}: {len(df):,} rows, {len(df.columns)} columns")
                
                # แสดง sample data
                logger.info(f"   Sample columns: {list(df.columns[:5])}")
                
            except FileNotFoundError:
                logger.error(f"❌ ไม่พบไฟล์: {filepath}")
                raise
            except Exception as e:
                logger.error(f"❌ Error loading {filename}: {str(e)}")
                raise
                
        logger.info(f"✅ โหลดข้อมูลทั้งหมดเสร็จสิ้น: {len(self.dataframes)} tables")
        
    def validate_data(self):
        """
        ตรวจสอบคุณภาพข้อมูล
        """
        logger.info("🔍 ตรวจสอบคุณภาพข้อมูล...")
        
        validation_report = {}
        
        for table_name, df in self.dataframes.items():
            report = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'missing_values': df.isnull().sum().sum(),
                'duplicate_rows': df.duplicated().sum(),
                'data_types': df.dtypes.to_dict()
            }
            
            # ตรวจสอบ key columns
            key_checks = {}
            if table_name in ['actual_cost', 'summary_cost']:
                key_checks['missing_project_id'] = df['project_id'].isnull().sum()
                key_checks['missing_g_code'] = df['g_code'].isnull().sum()
                key_checks['negative_budget'] = (df.get('total_budget', pd.Series([0])) < 0).sum()
                
            elif table_name == 'progress_payment':
                key_checks['missing_project_no'] = df['project_no'].isnull().sum()
                key_checks['negative_amounts'] = (df['progress_submit'] < 0).sum()
                
            report['key_validations'] = key_checks
            validation_report[table_name] = report
            
            # Log summary
            logger.info(f"📊 {table_name}:")
            logger.info(f"   - Rows: {report['total_rows']:,}")
            logger.info(f"   - Missing values: {report['missing_values']:,}")
            logger.info(f"   - Duplicates: {report['duplicate_rows']:,}")
            
            if key_checks:
                for check, value in key_checks.items():
                    if value > 0:
                        logger.warning(f"   ⚠️ {check}: {value}")
        
        # Save validation report
        report_file = f"{self.output_dir}/quality_reports/data_validation_report.json"
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, ensure_ascii=False, default=str)
            
        logger.info(f"📋 Validation report saved: {report_file}")
        return validation_report
        
    def clean_data(self):
        """
        ทำความสะอาดข้อมูล
        """
        logger.info("🧹 ทำความสะอาดข้อมูล...")
        
        for table_name, df in self.dataframes.items():
            original_rows = len(df)
            
            # ลบ duplicates
            df_clean = df.drop_duplicates()
            
            # ทำความสะอาดตาม table
            if table_name in ['actual_cost', 'summary_cost']:
                # ลบ rows ที่ไม่มี project_id หรือ g_code
                df_clean = df_clean.dropna(subset=['project_id', 'g_code'])
                
                # แทนที่ negative values ด้วย 0 (ยกเว้น variance ที่อาจติดลบได้)
                numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
                exclude_cols = ['variance_budget', 'cost_saving', 'bg_balance', 'budget_balance_ac', 'budget_balance_pu']
                
                for col in numeric_cols:
                    if col not in exclude_cols:
                        df_clean[col] = df_clean[col].clip(lower=0)
                
            elif table_name == 'progress_payment':
                # ลบ rows ที่ไม่มี project_no
                df_clean = df_clean.dropna(subset=['project_no'])
                
                # แก้ไข negative payment amounts
                payment_cols = ['progress_submit', 'certificate', 'submit_balance']
                for col in payment_cols:
                    if col in df_clean.columns:
                        df_clean[col] = df_clean[col].clip(lower=0)
            
            # Update dataframe
            self.dataframes[table_name] = df_clean
            
            cleaned_rows = len(df_clean)
            removed_rows = original_rows - cleaned_rows
            
            logger.info(f"🧹 {table_name}: ลบ {removed_rows:,} rows, เหลือ {cleaned_rows:,} rows")
            
    def create_master_schema(self):
        """
        รวมข้อมูลเป็น Master Schema
        """
        logger.info("🔗 สร้าง Master Schema...")
        
        # เริ่มจาก actual_cost เป็นฐาน
        master = self.dataframes['actual_cost'].copy()
        logger.info(f"📊 เริ่มจาก Actual Cost: {len(master):,} rows")
        
        # Join กับ summary_cost
        summary_cols = [
            'project_id', 'g_code', 's_code', 'month', 'year',
            'purchase_cost', 'forecast', 'variance_budget', 'cost_variance_pct',
            'purchase_efficiency', 'risk_high_variance', 'risk_forecast_overrun'
        ]
        
        summary_data = self.dataframes['summary_cost'][summary_cols].copy()
        
        master = master.merge(
            summary_data,
            on=['project_id', 'g_code', 's_code', 'month', 'year'],
            how='left',
            suffixes=('', '_summary')
        )
        logger.info(f"📊 หลัง join Summary Cost: {len(master):,} rows")
        
        # Aggregate progress_payment ตามเดือน
        progress_agg = self.dataframes['progress_payment'].groupby(
            ['project_no', 'month', 'year']
        ).agg({
            'progress_submit': 'sum',
            'certificate': 'sum', 
            'submit_balance': 'sum'
        }).reset_index()
        
        progress_agg = progress_agg.rename(columns={'project_no': 'project_id'})
        
        master = master.merge(
            progress_agg,
            on=['project_id', 'month', 'year'],
            how='left',
            suffixes=('', '_payment')
        )
        logger.info(f"📊 หลัง join Progress Payment: {len(master):,} rows")
        
        # Join กับ projects_master
        projects_info = self.dataframes['projects_master'].copy()
        
        master = master.merge(
            projects_info,
            on='project_id',
            how='left'
        )
        logger.info(f"📊 หลัง join Projects Master: {len(master):,} rows")
        
        # Join กับ cost_codes_master  
        cost_codes_info = self.dataframes['cost_codes_master'][['g_code', 's_code', 'description']].copy()
        cost_codes_info = cost_codes_info.rename(columns={'description': 'cost_code_description'})
        
        master = master.merge(
            cost_codes_info,
            on=['g_code', 's_code'],
            how='left',
            suffixes=('', '_code')
        )
        logger.info(f"📊 หลัง join Cost Codes: {len(master):,} rows")
        
        self.master_data = master
        logger.info(f"✅ Master Schema สร้างเสร็จ: {len(master):,} rows, {len(master.columns)} columns")
        
    def add_derived_features(self):
        """
        เพิ่ม derived features และ calculations
        """
        logger.info("⚙️ สร้าง Derived Features...")
        
        df = self.master_data.copy()
        
        # === Time-based features ===
        # สร้าง date column จาก year และ month
        df['date_str'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2) + '-01'
        df['date'] = pd.to_datetime(df['date_str'], format='%Y-%m-%d')
        df = df.drop('date_str', axis=1)  # ลบ temp column
        
        # ใช้ค่าที่มีอยู่แล้วจาก mockup หรือสร้างใหม่ถ้าไม่มี
        if 'quarter' not in df.columns:
            df['quarter'] = ((df['month'] - 1) // 3) + 1
        if 'is_year_end' not in df.columns:
            df['is_year_end'] = (df['month'] == 12).astype(int)
            
        df['days_from_start'] = (df['date'] - pd.to_datetime('2024-01-01')).dt.days
        
        # === Financial Performance Metrics ===
        # ตรวจสอบและใช้ข้อมูลที่มีอยู่แล้วจาก mockup หรือคำนวณใหม่
        if 'cpi' not in df.columns:
            df['cpi'] = np.where(df['total_actual'] > 0, df['total_budget'] / df['total_actual'], 1.0)
        if 'spi' not in df.columns:
            expected_progress = (df['month'] / 12) * 100
            df['spi'] = np.where(expected_progress > 0, df['progress_percentage'] / expected_progress, 1.0)
        if 'budget_utilization_pct' not in df.columns:
            df['budget_utilization_pct'] = (df['total_actual'] / df['total_budget']) * 100
        if 'progress_cost_ratio' not in df.columns:
            df['progress_cost_ratio'] = np.where(
                df['budget_utilization_pct'] > 0,
                df['progress_percentage'] / df['budget_utilization_pct'],
                1.0
            )
        
        # === เพิ่ม Advanced Metrics ===
        # BCWP (Budgeted Cost of Work Performed)
        df['bcwp'] = df['total_budget'] * (df['progress_percentage'] / 100)
        
        # ACWP (Actual Cost of Work Performed)  
        df['acwp'] = df['total_actual']
        
        # BCWS (Budgeted Cost of Work Scheduled) - สมมติ schedule linear
        expected_progress = (df['month'] / 12) * 100  # สมมติ 12 เดือนเสร็จ
        df['bcws'] = df['total_budget'] * (expected_progress / 100)
        
        # Schedule Variance (SV) และ Cost Variance (CV)
        df['schedule_variance'] = df['bcwp'] - df['bcws']
        df['cost_variance'] = df['bcwp'] - df['acwp']
        
        # ป้องกันการหารด้วย 0
        df['cost_variance_pct'] = np.where(
            df['bcwp'] > 0,
            (df['cost_variance'] / df['bcwp']) * 100,
            0
        )
        
        # Estimate at Completion (EAC)
        df['eac'] = np.where(
            df['cpi'] > 0,
            df['total_budget'] / df['cpi'],
            df['total_budget'] * 2  # fallback ถ้า CPI = 0
        )
        
        # Variance at Completion (VAC)
        df['vac'] = df['total_budget'] - df['eac']
        
        # === Efficiency Metrics ===
        # Cost Efficiency
        df['cost_efficiency'] = np.where(
            df['total_actual'] > 0,
            df['total_budget'] / df['total_actual'],
            1.0
        )
        
        # Progress Efficiency  
        df['progress_efficiency'] = np.where(
            expected_progress > 0,
            df['progress_percentage'] / expected_progress,
            1.0
        )
        
        # Overall Efficiency Score (0-100)
        df['efficiency_score'] = (
            (df['cost_efficiency'].clip(0, 2) * 0.4) +
            (df['progress_efficiency'].clip(0, 2) * 0.4) +
            (df['cpi'].clip(0, 2) * 0.2)
        ) * 50  # normalize เป็น 0-100
        
        # === Risk Scores ===
        # Cost Risk Score (0-100, 100 = highest risk)
        df['cost_risk_score'] = np.where(
            df['budget_utilization_pct'] > 100,
            np.minimum(100, (df['budget_utilization_pct'] - 100) * 2),  # 150% = 100 risk
            np.maximum(0, 50 - df['budget_utilization_pct'] / 2)  # <50% also risky (too slow)
        )
        
        # Schedule Risk Score
        df['schedule_risk_score'] = np.where(
            df['progress_percentage'] < expected_progress,
            np.minimum(100, (expected_progress - df['progress_percentage']) * 2),
            0  # ahead of schedule = no risk
        )
        
        # Combined Risk Score
        df['overall_risk_score'] = (
            df['cost_risk_score'] * 0.6 +
            df['schedule_risk_score'] * 0.4
        )
        
        # === Cash Flow Metrics ===
        # Monthly Cash Burn Rate - ป้องกันการหารด้วย 0
        df['monthly_burn_rate'] = np.where(
            df['month'] > 0,
            df['total_actual'] / df['month'],
            0
        )
        
        # Projected Monthly Spending (เดือนหน้า)
        df['projected_next_month_cost'] = df['monthly_burn_rate'] * 1.1  # เพิ่ม 10%
        
        # Cash Flow Forecast (3 เดือนข้างหน้า)
        df['cash_flow_3m_forecast'] = df['projected_next_month_cost'] * 3
        
        # === Status Classifications ===
        # Project Health Status
        def get_health_status(row):
            if row['overall_risk_score'] >= 70:
                return 'Critical'
            elif row['overall_risk_score'] >= 40:
                return 'Warning'
            elif row['overall_risk_score'] >= 20:
                return 'Caution'
            else:
                return 'Healthy'
                
        df['health_status'] = df.apply(get_health_status, axis=1)
        
        # Performance Category
        def get_performance_category(row):
            if row['efficiency_score'] >= 80:
                return 'Excellent'
            elif row['efficiency_score'] >= 60:
                return 'Good'
            elif row['efficiency_score'] >= 40:
                return 'Fair'
            else:
                return 'Poor'
                
        df['performance_category'] = df.apply(get_performance_category, axis=1)
        
        # === Update master data ===
        self.master_data = df
        
        new_features = [
            'bcwp', 'acwp', 'bcws', 'schedule_variance', 'cost_variance', 'cost_variance_pct',
            'eac', 'vac', 'cost_efficiency', 'progress_efficiency', 'efficiency_score',
            'cost_risk_score', 'schedule_risk_score', 'overall_risk_score',
            'monthly_burn_rate', 'projected_next_month_cost', 'cash_flow_3m_forecast',
            'health_status', 'performance_category'
        ]
        
        logger.info(f"✅ เพิ่ม Derived Features: {len(new_features)} features")
        logger.info(f"📊 Total columns: {len(df.columns)}")
        
    def create_alert_flags(self):
        """
        สร้าง Alert Flags ตาม Business Logic
        """
        logger.info("🚨 สร้าง Alert Flags...")
        
        df = self.master_data.copy()
        
        # === Primary Alerts (จากแผนงาน) ===
        # 1. Cost Overrun Alert
        df['alert_cost_overrun'] = (df['total_actual'] > df['total_budget']).astype(int)
        
        # 2. Progress Lag Alert  
        df['alert_progress_lag'] = (
            df['total_actual'] > (df['progress_percentage'] * df['total_budget'] / 100 * 1.5)
        ).astype(int)
        
        # 3. Profit Risk Alert (ใช้ profit margin แทน absolute profit)
        # ตรวจสอบว่ามี contract_value หรือไม่
        if 'contract_value' in df.columns:
            profit_margin = ((df['contract_value'] - df['total_actual']) / df['contract_value']) * 100
            df['profit_margin'] = profit_margin
            df['alert_profit_risk'] = (profit_margin < -10).astype(int)  # น้อยกว่า -10%
        else:
            # ถ้าไม่มี contract_value ใช้ total_budget แทน
            profit_margin = ((df['total_budget'] - df['total_actual']) / df['total_budget']) * 100
            df['profit_margin'] = profit_margin
            df['alert_profit_risk'] = (profit_margin < -10).astype(int)
        
        # === Secondary Alerts ===
        # 4. High Variance Alert - ตรวจสอบ column ที่มีอยู่
        if 'cost_variance_pct' in df.columns:
            df['alert_high_variance'] = (abs(df['cost_variance_pct']) > 25).astype(int)
        else:
            # คำนวณ variance ใหม่ถ้าไม่มี
            variance_pct = ((df['total_actual'] - df['total_budget']) / df['total_budget']) * 100
            df['alert_high_variance'] = (abs(variance_pct) > 25).astype(int)
        
        # 5. Schedule Delay Alert
        expected_progress = (df['month'] / 12) * 100
        df['alert_schedule_delay'] = (df['progress_percentage'] < expected_progress * 0.8).astype(int)
        
        # 6. Cash Flow Risk Alert - ตรวจสอบ contract_value
        if 'contract_value' in df.columns:
            df['alert_cash_flow_risk'] = (df['cash_flow_3m_forecast'] > df['contract_value'] * 0.3).astype(int)
        else:
            df['alert_cash_flow_risk'] = (df['cash_flow_3m_forecast'] > df['total_budget'] * 0.5).astype(int)
        
        # 7. Efficiency Alert
        df['alert_low_efficiency'] = (df['efficiency_score'] < 40).astype(int)
        
        # 8. Forecast Overrun Alert
        df['alert_forecast_overrun'] = (df['eac'] > df['total_budget'] * 1.15).astype(int)
        
        # === Alert Severity Calculation ===
        # นับจำนวน alerts
        alert_columns = [col for col in df.columns if col.startswith('alert_')]
        df['total_alerts'] = df[alert_columns].sum(axis=1)
        
        # แบ่งระดับความรุนแรง
        def get_alert_severity(row):
            critical_alerts = row['alert_cost_overrun'] + row['alert_profit_risk'] + row['alert_forecast_overrun']
            total_alerts = row['total_alerts']
            
            if critical_alerts >= 2 or total_alerts >= 5:
                return 'Critical'
            elif critical_alerts >= 1 or total_alerts >= 3:
                return 'High'
            elif total_alerts >= 1:
                return 'Medium'
            else:
                return 'Low'
                
        df['alert_severity'] = df.apply(get_alert_severity, axis=1)
        
        # Alert Level (สำหรับ UI)
        severity_map = {'Critical': 'Red', 'High': 'Red', 'Medium': 'Yellow', 'Low': 'Green'}
        df['alert_level'] = df['alert_severity'].map(severity_map)
        
        # === Alert Summary ===
        alert_summary = df.groupby('alert_level').size().to_dict()
        logger.info(f"🚨 Alert Summary: {alert_summary}")
        
        # Alert by project
        project_alerts = df.groupby('project_id')['alert_severity'].apply(
            lambda x: x.value_counts().to_dict()
        ).to_dict()
        
        self.master_data = df
        logger.info(f"✅ สร้าง Alert Flags เสร็จ: {len(alert_columns)} alert types")
        
        return alert_summary, project_alerts
    
    def export_data(self):
        """
        Export ข้อมูลที่ประมวลผลแล้ว
        """
        logger.info("💾 Export ข้อมูล...")
        
        # === Main Master Data ===
        master_file = f"{self.output_dir}/master_data.csv"
        self.master_data.to_csv(master_file, index=False, encoding='utf-8-sig')
        logger.info(f"✅ Master Data: {master_file} ({len(self.master_data):,} rows)")
        
        # === Features for ML ===
        # เลือกเฉพาะ features ที่จำเป็นสำหรับ ML
        ml_features = [
            # Identifiers
            'project_id', 'g_code', 's_code', 'month', 'year',
            
            # Financial metrics (เลือกที่มีแน่นอน)
            'total_budget', 'total_actual', 'progress_percentage', 
            'cpi', 'spi', 'budget_utilization_pct',
            'bcwp', 'acwp', 'bcws', 'cost_variance', 'schedule_variance',
            'eac', 'vac', 'efficiency_score',
            
            # Risk metrics
            'cost_risk_score', 'schedule_risk_score', 'overall_risk_score',
            'monthly_burn_rate', 'projected_next_month_cost',
            
            # Target variables / Labels
            'alert_cost_overrun', 'alert_progress_lag', 'alert_profit_risk',
            'alert_severity', 'health_status', 'performance_category',
            'total_alerts', 'alert_level'
        ]
        
        # เพิ่ม optional columns ถ้ามี
        optional_features = ['quarter', 'progress_cost_ratio', 'contract_value', 'project_name']
        for feature in optional_features:
            if feature in self.master_data.columns:
                ml_features.append(feature)
        
        # ตรวจสอบว่า columns มีอยู่
        available_features = [col for col in ml_features if col in self.master_data.columns]
        missing_features = [col for col in ml_features if col not in self.master_data.columns]
        
        if missing_features:
            logger.warning(f"⚠️ Missing features: {missing_features}")
        
        ml_data = self.master_data[available_features].copy()
        ml_file = f"{self.output_dir}/ml_features.csv"
        ml_data.to_csv(ml_file, index=False, encoding='utf-8-sig')
        logger.info(f"✅ ML Features: {ml_file} ({len(ml_data):,} rows, {len(available_features)} features)")
        
        # === Summary Reports ===
        # Project summary
        def get_most_common_alert_level(series):
            """หา alert level ที่เกิดขึ้นบ่อยที่สุด"""
            try:
                mode_result = series.mode()
                if len(mode_result) > 0:
                    return mode_result.iloc[0]
                else:
                    return 'Green'
            except:
                return 'Green'
        
        project_summary = self.master_data.groupby('project_id').agg({
            'total_budget': 'sum',
            'total_actual': 'sum', 
            'progress_percentage': 'mean',
            'efficiency_score': 'mean',
            'overall_risk_score': 'mean',
            'total_alerts': 'sum',
            'alert_level': get_most_common_alert_level
        }).round(2)
        
        project_summary_file = f"{self.output_dir}/project_summary.csv"
        project_summary.to_csv(project_summary_file, encoding='utf-8-sig')
        logger.info(f"✅ Project Summary: {project_summary_file}")
        
        # Cost Code summary  
        cost_code_summary = self.master_data.groupby(['g_code', 's_code']).agg({
            'total_budget': 'sum',
            'total_actual': 'sum',
            'budget_utilization_pct': 'mean', 
            'cost_risk_score': 'mean',
            'total_alerts': 'sum'
        }).round(2)
        
        cost_code_file = f"{self.output_dir}/cost_code_summary.csv"
        cost_code_summary.to_csv(cost_code_file, encoding='utf-8-sig')
        logger.info(f"✅ Cost Code Summary: {cost_code_file}")
        
        # === Data Dictionary ===
        data_dict = {
            'master_data_columns': len(self.master_data.columns),
            'total_records': len(self.master_data),
            'date_range': f"{self.master_data['date'].min()} to {self.master_data['date'].max()}",
            'projects_count': self.master_data['project_id'].nunique(),
            'cost_codes_count': len(self.master_data.groupby(['g_code', 's_code'])),
            'alert_distribution': self.master_data['alert_level'].value_counts().to_dict(),
            'files_created': [
                master_file, ml_file, project_summary_file, cost_code_file
            ]
        }
        
        dict_file = f"{self.output_dir}/data_dictionary.json"
        import json
        with open(dict_file, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"✅ Data Dictionary: {dict_file}")
        
        return data_dict
    
    def run_etl_pipeline(self):
        """
        รันกระบวนการ ETL ทั้งหมด
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("🚀 เริ่ม ETL Pipeline สำหรับ AI Budget Alert Dashboard")
        logger.info("=" * 80)
        
        try:
            # Step 1: Load data
            self.load_data()
            
            # Step 2: Validate data quality
            validation_report = self.validate_data()
            
            # Step 3: Clean data
            self.clean_data()
            
            # Step 4: Create master schema
            self.create_master_schema()
            
            # Step 5: Add derived features
            self.add_derived_features()
            
            # Step 6: Create alert flags
            alert_summary, project_alerts = self.create_alert_flags()
            
            # Step 7: Export processed data
            data_dict = self.export_data()
            
            # Summary
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("=" * 80)
            logger.info("✅ ETL Pipeline เสร็จสิ้น!")
            logger.info(f"⏱️ ใช้เวลา: {duration}")
            logger.info(f"📊 ประมวลผล: {len(self.master_data):,} records")
            logger.info(f"📁 สร้างไฟล์: {len(data_dict['files_created'])} files")
            logger.info(f"🚨 Alert Summary: {alert_summary}")
            logger.info("=" * 80)
            
            return True, data_dict
            
        except Exception as e:
            logger.error(f"❌ ETL Pipeline ล้มเหลว: {str(e)}")
            return False, str(e)

# === MAIN EXECUTION ===
if __name__ == "__main__":
    # สร้าง ETL instance
    etl = BudgetETL(
        data_dir='data/raw/',
        output_dir='data/processed/'
    )
    
    # รัน ETL pipeline
    success, result = etl.run_etl_pipeline()
    
    if success:
        print("\n🎉 ETL สำเร็จ! ไฟล์ข้อมูลพร้อมใช้งาน:")
        print("📁 data/processed/master_data.csv - ข้อมูลหลักทั้งหมด")
        print("📁 data/processed/ml_features.csv - ข้อมูลสำหรับ ML")
        print("📁 data/processed/project_summary.csv - สรุปโครงการ")
        print("📁 data/processed/cost_code_summary.csv - สรุป Cost Code")
        print("\n🔧 ขั้นตอนถัดไป:")
        print("1. ตรวจสอบข้อมูลใน data/processed/")
        print("2. เริ่มพัฒนา Dashboard ด้วย Streamlit")
        print("3. เตรียม ML Models สำหรับ Forecasting")
    else:
        print(f"\n❌ ETL ล้มเหลว: {result}")
"""
Project Analysis Dashboard
กราฟและตารางวิเคราะห์โครงการด้วย EVM (Earned Value Management)
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, timedelta

class ProjectAnalysisDashboard:
    """Dashboard สำหรับวิเคราะห์โครงการ"""
    
    def __init__(self, data_file='data/processed/master_data.csv'):
        self.data_file = data_file
        self.load_data()
    
    def load_data(self):
        """โหลดข้อมูล"""
        try:
            self.df = pd.read_csv(self.data_file)
            self.df['date'] = pd.to_datetime(self.df['year'].astype(str) + '-' + 
                                           self.df['month'].astype(str).str.zfill(2) + '-01')
            
            # เพิ่มข้อมูลที่จำเป็นถ้าไม่มี
            if 'bcwp' not in self.df.columns:
                self._calculate_evm_metrics()
                
            print("✅ โหลดข้อมูลสำเร็จ")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            self.df = None
    
    def _calculate_evm_metrics(self):
        """คำนวณ EVM metrics จากข้อมูลที่มี"""
        # ตรวจสอบและสร้าง columns ที่จำเป็น
        
        # BCWP (Budgeted Cost of Work Performed) - ถ้ายังไม่มี
        if 'bcwp' not in self.df.columns:
            self.df['bcwp'] = self.df['total_budget'] * (self.df['progress_percentage'] / 100)
        
        # ACWP (Actual Cost of Work Performed) - ถ้ายังไม่มี
        if 'acwp' not in self.df.columns:
            self.df['acwp'] = self.df['total_actual']
        
        # BCWS (Budgeted Cost of Work Scheduled) - ถ้ายังไม่มี
        if 'bcws' not in self.df.columns:
            expected_progress = (self.df['month'] / 12) * 100
            self.df['bcws'] = self.df['total_budget'] * (expected_progress / 100)
        
        # สร้าง Contract Plan จาก BCWS (ใช้ S-curve)
        if 'contract_plan' not in self.df.columns:
            # ใช้ S-curve สำหรับแผนการใช้เงิน (realistic curve)
            s_curve_factor = np.sin((self.df['month'] / 12) * np.pi / 2) ** 1.5
            self.df['contract_plan'] = self.df['total_budget'] * s_curve_factor
        
        # CPI (Cost Performance Index) - ถ้ายังไม่มีหรือเป็น NaN
        if 'cpi' not in self.df.columns or self.df['cpi'].isna().all():
            self.df['cpi'] = np.where(self.df['acwp'] > 0, self.df['bcwp'] / self.df['acwp'], 1.0)
        
        # SPI (Schedule Performance Index) - ถ้ายังไม่มีหรือเป็น NaN
        if 'spi' not in self.df.columns or self.df['spi'].isna().all():
            self.df['spi'] = np.where(self.df['bcws'] > 0, self.df['bcwp'] / self.df['bcws'], 1.0)
        
        # EAC (Estimate at Completion) - ถ้ายังไม่มี
        if 'eac' not in self.df.columns:
            self.df['eac'] = np.where(self.df['cpi'] > 0, self.df['total_budget'] / self.df['cpi'], self.df['total_budget'] * 2)
        
        # VAC (Variance at Completion) - ถ้ายังไม่มี
        if 'vac' not in self.df.columns:
            self.df['vac'] = self.df['total_budget'] - self.df['eac']
        
        # Forecast - ใช้จากข้อมูลที่มี หรือ EAC
        if 'forecast' not in self.df.columns:
            self.df['forecast'] = self.df['eac']
    
    def get_project_list(self):
        """ดึงรายการโครงการ"""
        return self.df['project_id'].unique().tolist()
    
    def filter_project_data(self, project_id):
        """กรองข้อมูลตาม project และคำนวณ progress ตามที่ต้องการ"""
        project_data = self.df[self.df['project_id'] == project_id].copy()
        
        # ตรวจสอบ columns ที่มีอยู่
        available_columns = project_data.columns.tolist()
        
        # กำหนด columns พื้นฐานที่ต้องใช้
        base_columns = {
            'total_budget': 'sum',
            'total_actual': 'sum', 
            'bcwp': 'sum',
            'acwp': 'sum',
            'bcws': 'sum'
        }
        
        # เพิ่ม progress_submit และ certificate
        payment_columns = {
            'progress_submit': 'sum',
            'certificate': 'sum',
            'submit_balance': 'sum'
        }
        
        # รวม columns ที่ต้องใช้
        agg_dict = {}
        for col, agg_func in base_columns.items():
            if col in available_columns:
                agg_dict[col] = agg_func
        
        for col, agg_func in payment_columns.items():
            if col in available_columns:
                agg_dict[col] = agg_func
        
        # เพิ่ม contract_plan เฉพาะเมื่อมี
        if 'contract_plan' in available_columns:
            agg_dict['contract_plan'] = 'sum'
            
        # เพิ่ม columns เสริม
        optional_columns = {
            'forecast': 'sum',
            'eac': 'sum',
            'vac': 'sum',
            'contract_value': 'first',
            'project_name': 'first'
        }
        
        for col, agg_func in optional_columns.items():
            if col in available_columns:
                agg_dict[col] = agg_func
        
        # Aggregate รายเดือน
        try:
            monthly_data = project_data.groupby(['month', 'year', 'date']).agg(agg_dict).reset_index()
            monthly_data = monthly_data.sort_values('month').reset_index(drop=True)
        except Exception as e:
            st.error(f"Error aggregating data: {e}")
            return pd.DataFrame(), pd.DataFrame()
        
        # คำนวณ % Progress ตามที่ต้องการ
        
        # 1. % Progress จาก progress_submit (สะสมรายเดือน)
        if 'progress_submit' in monthly_data.columns:
            monthly_data['progress_submit_cumulative'] = monthly_data['progress_submit'].cumsum()
            
            # คำนวณ % จาก contract_value หรือ total budget
            contract_value = monthly_data['contract_value'].iloc[0] if 'contract_value' in monthly_data.columns else monthly_data['total_budget'].iloc[0]
            monthly_data['progress_percentage'] = (monthly_data['progress_submit_cumulative'] / contract_value) * 100
            
            # ปรับให้ไม่เกิน 100%
            monthly_data['progress_percentage'] = monthly_data['progress_percentage'].clip(upper=100)
        else:
            # ถ้าไม่มี progress_submit ใช้วิธีคำนวณจาก actual/budget
            monthly_data['progress_percentage'] = (monthly_data['total_actual'] / monthly_data['total_budget']) * 100
            monthly_data['progress_percentage'] = monthly_data['progress_percentage'].clip(upper=100)
        
        # คำนวณ metrics อื่นๆ
        if 'acwp' in monthly_data.columns and 'bcwp' in monthly_data.columns:
            monthly_data['cpi'] = np.where(monthly_data['acwp'] > 0, monthly_data['bcwp'] / monthly_data['acwp'], 1.0)
        
        if 'bcws' in monthly_data.columns and 'bcwp' in monthly_data.columns:
            monthly_data['spi'] = np.where(monthly_data['bcws'] > 0, monthly_data['bcwp'] / monthly_data['bcws'], 1.0)
        
        if 'total_budget' in monthly_data.columns and 'cpi' in monthly_data.columns:
            monthly_data['eac'] = np.where(monthly_data['cpi'] > 0, monthly_data['total_budget'] / monthly_data['cpi'], monthly_data['total_budget'] * 2)
        
        if 'total_budget' in monthly_data.columns and 'eac' in monthly_data.columns:
            monthly_data['vac'] = monthly_data['total_budget'] - monthly_data['eac']
        
        return monthly_data, project_data
        
    def analyze_progress_data(self, project_id):
        """วิเคราะห์ข้อมูล Progress เพื่อดูวิธีการคำนวณต่างๆ"""
        project_data = self.df[self.df['project_id'] == project_id].copy()
        
        # ข้อมูลดิบ progress รายเดือน
        available_columns = project_data.columns.tolist()
        
        # Aggregate ข้อมูลรายเดือน
        agg_dict = {
            'total_actual': 'sum',
            'total_budget': 'sum'
        }
        
        # เพิ่ม columns ตามที่มี
        optional_columns = ['progress_percentage', 'progress_submit', 'certificate', 'bcwp']
        for col in optional_columns:
            if col in available_columns:
                if col == 'progress_percentage':
                    agg_dict[col] = 'mean'
                else:
                    agg_dict[col] = 'sum'
        
        raw_progress = project_data.groupby('month').agg(agg_dict).reset_index().sort_values('month')
        
        # คำนวณหลายแบบเพื่อเปรียบเทียบ
        contract_value = raw_progress['total_budget'].iloc[0] if len(raw_progress) > 0 else 1
        
        # 1. Progress แบบเดิม (จาก mockup)
        if 'progress_percentage' in raw_progress.columns:
            raw_progress['progress_original'] = raw_progress['progress_percentage']
        else:
            raw_progress['progress_original'] = 0
        
        # 2. Progress จาก Certificate (ถ้ามี)
        if 'certificate' in raw_progress.columns:
            raw_progress['certificate_cumulative'] = raw_progress['certificate'].cumsum()
            raw_progress['progress_from_certificate'] = (raw_progress['certificate_cumulative'] / contract_value) * 100
        else:
            raw_progress['progress_from_certificate'] = 0
            
        # 3. Progress จาก Submit (ถ้ามี)
        if 'progress_submit' in raw_progress.columns:
            raw_progress['submit_cumulative'] = raw_progress['progress_submit'].cumsum()
            raw_progress['progress_from_submit'] = (raw_progress['submit_cumulative'] / contract_value) * 100
        else:
            raw_progress['progress_from_submit'] = 0
        
        # 4. Progress จาก BCWP (ถ้ามี)
        if 'bcwp' in raw_progress.columns:
            raw_progress['bcwp_cumulative'] = raw_progress['bcwp'].cumsum()
            raw_progress['progress_from_bcwp'] = (raw_progress['bcwp_cumulative'] / contract_value) * 100
        else:
            raw_progress['progress_from_bcwp'] = 0
        
        # 5. S-curve Progress (realistic simulation)
        total_months = len(raw_progress)
        s_curve_progress = []
        for i in range(total_months):
            month_ratio = (i + 1) / total_months
            # S-curve formula
            progress_value = 100 * (3 * month_ratio**2 - 2 * month_ratio**3)
            s_curve_progress.append(progress_value)
        raw_progress['progress_s_curve'] = s_curve_progress
        
        # ปรับให้ไม่เกิน 100%
        for col in ['progress_from_certificate', 'progress_from_submit', 'progress_from_bcwp']:
            if col in raw_progress.columns:
                raw_progress[col] = raw_progress[col].clip(upper=100)
        
        return raw_progress
    
    def create_progress_comparison_chart(self, project_id):
        """สร้างกราฟเปรียบเทียบ Progress หลายแบบ"""
        progress_data = self.analyze_progress_data(project_id)
        
        if progress_data.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        # Progress แบบเดิม (จาก mockup)
        if 'progress_original' in progress_data.columns and progress_data['progress_original'].sum() > 0:
            fig.add_trace(go.Scatter(
                x=progress_data['month'],
                y=progress_data['progress_original'],
                mode='lines+markers',
                name='Progress Original (Mockup)',
                line=dict(color='red', width=2, dash='dot'),
                marker=dict(size=6)
            ))
        
        # Progress จาก Certificate
        if 'progress_from_certificate' in progress_data.columns and progress_data['progress_from_certificate'].sum() > 0:
            fig.add_trace(go.Scatter(
                x=progress_data['month'],
                y=progress_data['progress_from_certificate'],
                mode='lines+markers',
                name='Progress from Certificate 💰',
                line=dict(color='green', width=3),
                marker=dict(size=8)
            ))
        
        # Progress จาก Submit
        if 'progress_from_submit' in progress_data.columns and progress_data['progress_from_submit'].sum() > 0:
            fig.add_trace(go.Scatter(
                x=progress_data['month'],
                y=progress_data['progress_from_submit'],
                mode='lines+markers',
                name='Progress from Submit 📊',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))
        
        # Progress จาก BCWP
        if 'progress_from_bcwp' in progress_data.columns and progress_data['progress_from_bcwp'].sum() > 0:
            fig.add_trace(go.Scatter(
                x=progress_data['month'],
                y=progress_data['progress_from_bcwp'],
                mode='lines+markers',
                name='Progress from BCWP 📈',
                line=dict(color='orange', width=2),
                marker=dict(size=6)
            ))
        
        # S-curve Progress (realistic)
        fig.add_trace(go.Scatter(
            x=progress_data['month'],
            y=progress_data['progress_s_curve'],
            mode='lines+markers',
            name='S-Curve Progress (Ideal) ✨',
            line=dict(color='purple', width=2, dash='dash'),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title=f'📈 Progress Calculation Methods - {project_id}',
            xaxis_title='เดือน',
            yaxis_title='Progress (%)',
            hovermode='x unified',
            legend=dict(x=0.02, y=0.98),
            height=500,
            template='plotly_white',
            yaxis=dict(range=[0, 105])
        )
        
        return fig
    
    def analyze_progress_data(self, project_id):
        """วิเคราะห์ข้อมูล Progress เพื่อดูปัญหาการขึ้นลง"""
        project_data = self.df[self.df['project_id'] == project_id].copy()
        
        # ข้อมูลดิบ progress รายเดือน
        raw_progress = project_data.groupby('month').agg({
            'progress_percentage': 'mean',
            'total_actual': 'sum',
            'total_budget': 'sum',
            'bcwp': 'sum' if 'bcwp' in project_data.columns else 'mean'
        }).reset_index()
        
        # คำนวณ cumulative progress ที่ถูกต้อง
        if 'bcwp' in raw_progress.columns and 'total_budget' in raw_progress.columns:
            raw_progress['progress_from_bcwp'] = (raw_progress['bcwp'] / raw_progress['total_budget']) * 100
        else:
            raw_progress['progress_from_bcwp'] = raw_progress['progress_percentage']
        
        # คำนวณ cumulative
        raw_progress = raw_progress.sort_values('month')
        raw_progress['cumulative_progress'] = raw_progress['progress_from_bcwp']
        
        for i in range(1, len(raw_progress)):
            if raw_progress.iloc[i]['cumulative_progress'] < raw_progress.iloc[i-1]['cumulative_progress']:
                raw_progress.iloc[i, raw_progress.columns.get_loc('cumulative_progress')] = raw_progress.iloc[i-1]['cumulative_progress']
        
        return raw_progress
    
    def create_progress_comparison_chart(self, project_id):
        """สร้างกราฟเปรียบเทียบ Progress แบบเดิมกับแบบแก้ไข"""
        progress_data = self.analyze_progress_data(project_id)
        
        if progress_data.empty:
            return go.Figure()
        
        fig = go.Figure()
        
        # Progress แบบเดิม (ขึ้นลง)
        fig.add_trace(go.Scatter(
            x=progress_data['month'],
            y=progress_data['progress_percentage'],
            mode='lines+markers',
            name='Progress แบบเดิม (ผิด)',
            line=dict(color='red', width=2, dash='dot'),
            marker=dict(size=6)
        ))
        
        # Progress แบบแก้ไข (Cumulative)
        fig.add_trace(go.Scatter(
            x=progress_data['month'],
            y=progress_data['cumulative_progress'],
            mode='lines+markers',
            name='Progress แบบแก้ไข (ถูก)',
            line=dict(color='green', width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f'📈 เปรียบเทียบ Progress Calculation - {project_id}',
            xaxis_title='เดือน',
            yaxis_title='Progress (%)',
            hovermode='x unified',
            legend=dict(x=0.02, y=0.98),
            height=400,
            template='plotly_white'
        )
        
        return fig
    
    def create_chart_1(self, project_id):
        """
        กราฟ 1: Contract Plan vs Progress actual vs ACWP vs BCWP
        """
        monthly_data, _ = self.filter_project_data(project_id)
        
        if monthly_data.empty:
            st.error("ไม่มีข้อมูลสำหรับโครงการนี้")
            return go.Figure()
        
        fig = go.Figure()
        
        # Contract Plan - ใช้เฉพาะเมื่อมีข้อมูล
        if 'contract_plan' in monthly_data.columns and not monthly_data['contract_plan'].isna().all():
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['contract_plan'],
                mode='lines+markers',
                name='Contract Plan',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))
        
        # BCWS (Planned Value) - ใช้แทน Contract Plan ถ้าไม่มี
        if 'bcws' in monthly_data.columns:
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['bcws'],
                mode='lines+markers',
                name='BCWS (Planned Value)',
                line=dict(color='green', width=2, dash='dash'),
                marker=dict(size=6)
            ))
        
        # BCWP (Earned Value)
        if 'bcwp' in monthly_data.columns:
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['bcwp'],
                mode='lines+markers',
                name='BCWP (Earned Value)',
                line=dict(color='orange', width=3),
                marker=dict(size=8)
            ))
        
        # ACWP (Actual Cost)
        if 'acwp' in monthly_data.columns:
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['acwp'],
                mode='lines+markers',
                name='ACWP (Actual Cost)', 
                line=dict(color='red', width=3),
                marker=dict(size=8)
            ))
        elif 'total_actual' in monthly_data.columns:
            # ใช้ total_actual ถ้าไม่มี acwp
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['total_actual'],
                mode='lines+markers',
                name='Actual Cost', 
                line=dict(color='red', width=3),
                marker=dict(size=8)
            ))
        
        # Progress Line (secondary y-axis) - ใช้ progress ที่คำนวณใหม่
        if 'progress_percentage' in monthly_data.columns:
            # กำหนดชื่อ label ตามวิธีที่ใช้
            progress_label = 'Progress (%)'
            
            if 'certificate' in monthly_data.columns and monthly_data['certificate'].sum() > 0:
                progress_label = 'Progress (%) - from Certificate 💰'
            elif 'progress_submit' in monthly_data.columns and monthly_data['progress_submit'].sum() > 0:
                progress_label = 'Progress (%) - from Submit 📊'
            elif 'bcwp' in monthly_data.columns:
                progress_label = 'Progress (%) - from BCWP 📈'
            else:
                progress_label = 'Progress (%) - S-Curve Model ✨'
            
            fig.add_trace(go.Scatter(
                x=monthly_data['month'],
                y=monthly_data['progress_percentage'],
                mode='lines+markers',
                name=progress_label,
                line=dict(color='purple', width=3),
                marker=dict(size=8),
                yaxis='y2'
            ))
        
        fig.update_layout(
            title=f'📈 กราฟ 1: EVM Analysis - {project_id}',
            xaxis_title='เดือน',
            yaxis_title='จำนวนเงิน (บาท)',
            yaxis2=dict(
                title='Progress (%)',
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            hovermode='x unified',
            legend=dict(x=0.02, y=0.98),
            height=500,
            template='plotly_white'
        )
        
        return fig
    
    def create_chart_2(self, project_id):
        """
        กราฟ 2: Actual cost vs Forecast vs % progress
        """
        monthly_data, _ = self.filter_project_data(project_id)
        
        if monthly_data.empty:
            st.error("ไม่มีข้อมูลสำหรับโครงการนี้")
            return go.Figure()
        
        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            subplot_titles=[f'📊 กราฟ 2: Cost vs Forecast vs Progress - {project_id}']
        )
        
        # Actual Cost
        if 'total_actual' in monthly_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=monthly_data['month'],
                    y=monthly_data['total_actual'],
                    mode='lines+markers',
                    name='Actual Cost',
                    line=dict(color='red', width=3),
                    marker=dict(size=10)
                ),
                secondary_y=False
            )
        
        # Forecast - ใช้ EAC ถ้าไม่มี forecast
        forecast_data = None
        if 'forecast' in monthly_data.columns and not monthly_data['forecast'].isna().all():
            forecast_data = monthly_data['forecast']
            forecast_name = 'Forecast'
        elif 'eac' in monthly_data.columns:
            forecast_data = monthly_data['eac'] 
            forecast_name = 'EAC (Forecast)'
        
        if forecast_data is not None:
            fig.add_trace(
                go.Scatter(
                    x=monthly_data['month'],
                    y=forecast_data,
                    mode='lines+markers',
                    name=forecast_name,
                    line=dict(color='blue', width=2, dash='dot'),
                    marker=dict(size=8)
                ),
                secondary_y=False
            )
        
        # Budget Line (reference)
        if 'total_budget' in monthly_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=monthly_data['month'],
                    y=monthly_data['total_budget'],
                    mode='lines',
                    name='Budget',
                    line=dict(color='green', width=2, dash='dash'),
                    opacity=0.7
                ),
                secondary_y=False
            )
        
        # Progress %
        if 'progress_percentage' in monthly_data.columns:
            # กำหนดชื่อ label ตามวิธีที่ใช้
            progress_label = 'Progress (%)'
            
            if 'certificate' in monthly_data.columns and monthly_data['certificate'].sum() > 0:
                progress_label = 'Progress (%) - from Certificate 💰'
            elif 'progress_submit' in monthly_data.columns and monthly_data['progress_submit'].sum() > 0:
                progress_label = 'Progress (%) - from Submit 📊'
            elif 'bcwp' in monthly_data.columns:
                progress_label = 'Progress (%) - from BCWP 📈'
            else:
                progress_label = 'Progress (%) - S-Curve Model ✨'
            
            fig.add_trace(
                go.Scatter(
                    x=monthly_data['month'],
                    y=monthly_data['progress_percentage'],
                    mode='lines+markers',
                    name=progress_label,
                    line=dict(color='orange', width=3),
                    marker=dict(size=8),
                    fill='tonexty' if len(fig.data) == 0 else None,
                    fillcolor='rgba(255,165,0,0.2)'
                ),
                secondary_y=True
            )
        
        # Update axes
        fig.update_xaxes(title_text="เดือน")
        fig.update_yaxes(title_text="จำนวนเงิน (บาท)", secondary_y=False)
        fig.update_yaxes(title_text="Progress (%)", secondary_y=True, range=[0, 100])
        
        fig.update_layout(
            height=500,
            hovermode='x unified',
            legend=dict(x=0.02, y=0.98),
            template='plotly_white'
        )
        
        return fig
    
    def create_scode_table(self, project_id):
        """
        ตาราง: เปรียบเทียบ budget Amount vs Progress actual vs Actual cost vs % Actual cost vs BCWP vs ACWP vs EAC ของ s-code
        """
        _, project_data = self.filter_project_data(project_id)
        
        if project_data.empty:
            return pd.DataFrame()
        
        # Group by S-Code (latest month data)
        latest_month = project_data['month'].max()
        scode_data_filtered = project_data[project_data['month'] == latest_month]
        
        # ตรวจสอบ columns ที่มีอยู่
        available_columns = scode_data_filtered.columns.tolist()
        
        # กำหนด agg columns ที่ต้องการ
        agg_dict = {}
        required_agg_columns = {
            'total_budget': 'sum',
            'total_actual': 'sum',
            'progress_percentage': 'mean',
            'bcwp': 'sum',
            'acwp': 'sum',
            'eac': 'sum'
        }
        
        for col, agg_func in required_agg_columns.items():
            if col in available_columns:
                agg_dict[col] = agg_func
        
        # เพิ่ม description ถ้ามี
        if 'description' in available_columns:
            agg_dict['description'] = 'first'
        
        try:
            scode_data = scode_data_filtered.groupby(['g_code', 's_code']).agg(agg_dict).reset_index()
        except Exception as e:
            st.error(f"Error creating S-Code table: {e}")
            return pd.DataFrame()
        
        if scode_data.empty:
            return pd.DataFrame()
        
        # สร้าง cost_code
        scode_data['cost_code'] = scode_data['g_code'] + '-' + scode_data['s_code']
        
        # คำนวณ % Actual Cost
        if 'total_actual' in scode_data.columns and 'total_budget' in scode_data.columns:
            scode_data['actual_cost_pct'] = (scode_data['total_actual'] / scode_data['total_budget']) * 100
        else:
            scode_data['actual_cost_pct'] = 0
        
        # เลือก columns ที่จะแสดงตามที่ user ต้องการ
        display_columns = ['cost_code']
        
        # เพิ่ม description ถ้ามี
        if 'description' in scode_data.columns:
            display_columns.append('description')
        
        # เพิ่ม columns หลักที่ต้องการ
        main_columns = [
            'total_budget',      # Budget Amount
            'progress_percentage', # Progress Actual
            'total_actual',      # Actual Cost  
            'actual_cost_pct',   # % Actual Cost
            'bcwp',             # BCWP
            'acwp',             # ACWP
            'eac'               # EAC
        ]
        
        for col in main_columns:
            if col in scode_data.columns:
                display_columns.append(col)
        
        display_data = scode_data[display_columns].copy()
        
        # ปรับชื่อคอลัมน์ตามที่ต้องการ
        column_mapping = {
            'cost_code': 'Cost Code',
            'description': 'Description',
            'total_budget': 'Budget Amount',
            'progress_percentage': 'Progress Actual (%)',
            'total_actual': 'Actual Cost',
            'actual_cost_pct': '% Actual Cost',
            'bcwp': 'BCWP',
            'acwp': 'ACWP',
            'eac': 'EAC'
        }
        
        # เปลี่ยนชื่อเฉพาะที่มี
        rename_dict = {k: v for k, v in column_mapping.items() if k in display_data.columns}
        display_data = display_data.rename(columns=rename_dict)
        
        # จัดรูปแบบตัวเลข
        for col in display_data.columns:
            if col in ['Budget Amount', 'Actual Cost', 'BCWP', 'ACWP', 'EAC']:
                display_data[col] = display_data[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) and x != 0 else "0")
            elif col in ['Progress Actual (%)', '% Actual Cost']:
                display_data[col] = display_data[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%")
        
        return display_data
    
    def calculate_project_kpis(self, project_id):
        """
        คำนวณ KPIs ของโครงการ
        """
        monthly_data, _ = self.filter_project_data(project_id)
        
        if monthly_data.empty:
            # Return default values if no data
            default_kpis = {
                'BAC (Budget at Completion)': "0 บาท",
                'SPI (Schedule Performance Index)': "N/A",
                'CPI (Cost Performance Index)': "N/A",
                'ACWP (Actual Cost)': "0 บาท", 
                'BCWP (Earned Value)': "0 บาท",
                'BCWS (Planned Value)': "0 บาท",
                'EAC (Estimate at Completion)': "0 บาท",
                'VAC (Variance at Completion)': "0 บาท"
            }
            default_interpretations = {
                'SPI': "ไม่มีข้อมูล",
                'CPI': "ไม่มีข้อมูล",
                'VAC': "ไม่มีข้อมูล"
            }
            return default_kpis, default_interpretations, {}
        
        # ใช้ข้อมูลเดือนล่าสุด
        latest_data = monthly_data.iloc[-1]
        
        # BAC (Budget at Completion)
        bac = latest_data.get('total_budget', 0)
        
        # คำนวณ KPIs
        kpis = {
            'BAC (Budget at Completion)': f"{bac:,.0f} บาท",
        }
        
        # SPI - ตรวจสอบก่อนใช้
        if 'spi' in latest_data and pd.notna(latest_data['spi']):
            kpis['SPI (Schedule Performance Index)'] = f"{latest_data['spi']:.2f}"
        else:
            kpis['SPI (Schedule Performance Index)'] = "N/A"
        
        # CPI - ตรวจสอบก่อนใช้
        if 'cpi' in latest_data and pd.notna(latest_data['cpi']):
            kpis['CPI (Cost Performance Index)'] = f"{latest_data['cpi']:.2f}"
        else:
            kpis['CPI (Cost Performance Index)'] = "N/A"
        
        # ACWP
        acwp = latest_data.get('acwp', latest_data.get('total_actual', 0))
        kpis['ACWP (Actual Cost)'] = f"{acwp:,.0f} บาท"
        
        # BCWP
        bcwp = latest_data.get('bcwp', 0)
        kpis['BCWP (Earned Value)'] = f"{bcwp:,.0f} บาท"
        
        # BCWS
        bcws = latest_data.get('bcws', 0)
        kpis['BCWS (Planned Value)'] = f"{bcws:,.0f} บาท"
        
        # EAC
        eac = latest_data.get('eac', bac)
        kpis['EAC (Estimate at Completion)'] = f"{eac:,.0f} บาท"
        
        # VAC
        vac = latest_data.get('vac', bac - eac)
        kpis['VAC (Variance at Completion)'] = f"{vac:,.0f} บาท"
        
        # เพิ่มการตีความ
        interpretations = {}
        
        if 'spi' in latest_data and pd.notna(latest_data['spi']):
            interpretations['SPI'] = "ดี" if latest_data['spi'] >= 1.0 else "ล่าช้า"
        else:
            interpretations['SPI'] = "ไม่มีข้อมูล"
            
        if 'cpi' in latest_data and pd.notna(latest_data['cpi']):
            interpretations['CPI'] = "ดี" if latest_data['cpi'] >= 1.0 else "เกินงบ"
        else:
            interpretations['CPI'] = "ไม่มีข้อมูล"
            
        interpretations['VAC'] = "ประหยัด" if vac > 0 else "เกินงบ"
        
        return kpis, interpretations, latest_data
    
    def create_kpi_cards(self, kpis, interpretations):
        """สร้าง KPI Cards สำหรับแสดงผล"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            spi_value = kpis.get('SPI (Schedule Performance Index)', 'N/A')
            spi_interp = interpretations.get('SPI', 'ไม่มีข้อมูล')
            st.metric("SPI", spi_value, spi_interp)
        
        with col2:
            cpi_value = kpis.get('CPI (Cost Performance Index)', 'N/A')
            cpi_interp = interpretations.get('CPI', 'ไม่มีข้อมูล')
            st.metric("CPI", cpi_value, cpi_interp)
        
        with col3:
            eac_value = kpis.get('EAC (Estimate at Completion)', '0 บาท')
            st.metric("EAC", eac_value)
        
        with col4:
            vac_value = kpis.get('VAC (Variance at Completion)', '0 บาท')
            vac_interp = interpretations.get('VAC', '')
            st.metric("VAC", vac_value, vac_interp)

def main():
    """Main Streamlit App"""
    st.set_page_config(
        page_title="Project Analysis Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Project Analysis Dashboard")
    st.markdown("---")
    
    # สร้าง dashboard instance
    @st.cache_data
    def load_dashboard():
        return ProjectAnalysisDashboard()
    
    try:
        dashboard = load_dashboard()
    except Exception as e:
        st.error(f"❌ ไม่สามารถโหลด dashboard ได้: {e}")
        return
    
    if dashboard.df is None:
        st.error("❌ ไม่สามารถโหลดข้อมูลได้ ตรวจสอบไฟล์ data/processed/master_data.csv")
        st.info("💡 รัน ETL script ก่อน: `python etl_script.py`")
        return
    
    # แสดงข้อมูลพื้นฐาน
    st.sidebar.header("ℹ️ ข้อมูลที่มี")
    st.sidebar.write(f"📊 Records: {len(dashboard.df):,}")
    st.sidebar.write(f"📅 เดือน: {dashboard.df['month'].min()}-{dashboard.df['month'].max()}")
    st.sidebar.write(f"🗂️ Columns: {len(dashboard.df.columns)}")
    
    # แสดง columns ที่สำคัญ
    important_columns = ['bcwp', 'acwp', 'bcws', 'contract_plan', 'cpi', 'spi', 'eac']
    available_important = [col for col in important_columns if col in dashboard.df.columns]
    st.sidebar.write(f"✅ EVM Columns: {len(available_important)}/{len(important_columns)}")
    
    # ตรวจสอบ Progress Payment columns
    payment_columns = ['certificate', 'progress_submit', 'submit_balance']
    available_payment = [col for col in payment_columns if col in dashboard.df.columns]
    
    st.sidebar.write(f"\n📊 **Progress Calculation:**")
    if 'certificate' in available_payment and dashboard.df['certificate'].sum() > 0:
        st.sidebar.success("💰 Certificate Method (แม่นยำสุด)")
    elif 'progress_submit' in available_payment and dashboard.df['progress_submit'].sum() > 0:
        st.sidebar.info("📊 Submit Method (ดีรองลงมา)")  
    elif 'bcwp' in dashboard.df.columns:
        st.sidebar.warning("📈 BCWP Method")
    else:
        st.sidebar.warning("✨ S-Curve Model (จำลอง)")
    
    # Sidebar - Project Selection
    st.sidebar.header("🎯 เลือกโครงการ")
    project_list = dashboard.get_project_list()
    selected_project = st.sidebar.selectbox("เลือกโครงการ:", project_list)
    
    if selected_project:
        try:
            # KPI Section
            st.header(f"📈 KPIs Overview - {selected_project}")
            kpis, interpretations, latest_data = dashboard.calculate_project_kpis(selected_project)
            
            dashboard.create_kpi_cards(kpis, interpretations)
            
            # Detailed KPIs
            st.subheader("📊 Detailed Metrics")
            kpi_col1, kpi_col2 = st.columns(2)
            
            with kpi_col1:
                st.write("**Cost Metrics:**")
                st.write(f"• BAC: {kpis['BAC (Budget at Completion)']}")
                st.write(f"• ACWP: {kpis['ACWP (Actual Cost)']}")
                st.write(f"• EAC: {kpis['EAC (Estimate at Completion)']}")
                st.write(f"• VAC: {kpis['VAC (Variance at Completion)']}")
            
            with kpi_col2:
                st.write("**Performance Metrics:**")
                st.write(f"• BCWP: {kpis['BCWP (Earned Value)']}")
                st.write(f"• BCWS: {kpis['BCWS (Planned Value)']}")
                st.write(f"• SPI: {kpis['SPI (Schedule Performance Index)']} ({interpretations['SPI']})")
                st.write(f"• CPI: {kpis['CPI (Cost Performance Index)']} ({interpretations['CPI']})")
            
            st.markdown("---")
            
            # Charts Section
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.subheader("📈 กราฟ 1: EVM Analysis")
                try:
                    chart1 = dashboard.create_chart_1(selected_project)
                    st.plotly_chart(chart1, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Error creating Chart 1: {e}")
                    st.info("💡 บางข้อมูล EVM อาจไม่พร้อมใช้งาน")
            
            with chart_col2:
                st.subheader("📊 กราฟ 2: Cost vs Forecast")
                try:
                    chart2 = dashboard.create_chart_2(selected_project) 
                    st.plotly_chart(chart2, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Error creating Chart 2: {e}")
                    st.info("💡 ตรวจสอบข้อมูล forecast")
            
            # Table Section
            st.subheader("📋 ตาราง: Budget Amount vs Progress Actual vs Actual Cost vs % Actual Cost vs BCWP vs ACWP vs EAC")
            try:
                scode_table = dashboard.create_scode_table(selected_project)
                if not scode_table.empty:
                    st.dataframe(scode_table, use_container_width=True)
                else:
                    st.warning("⚠️ ไม่มีข้อมูล S-Code สำหรับโครงการนี้")
            except Exception as e:
                st.error(f"❌ Error creating S-Code table: {e}")
            
            # Progress Analysis Section (ปรับปรุงใหม่)
            with st.expander("🔍 Progress Calculation Analysis - วิธีคำนวณ % Progress"):
                st.write("**💡 Progress ของโครงการสามารถคำนวณได้หลายวิธี:**")
                
                col_method1, col_method2 = st.columns(2)
                
                with col_method1:
                    st.write("**📊 วิธีการคำนวณ Progress:**")
                    st.write("1. **Certificate** - เงินที่ได้รับจริงแล้ว (แม่นยำสุด)")
                    st.write("2. **Progress Submit** - เงินที่เสนอขอรับ")  
                    st.write("3. **BCWP/Budget** - มูลค่างานที่ทำเสร็จ")
                    st.write("4. **S-Curve** - โมเดลมาตรฐานโครงการ")
                    st.write("5. **Mockup Data** - ข้อมูลจำลอง (ไม่แม่นยำ)")
                
                with col_method2:
                    st.write("**✅ ข้อดี Certificate Method:**")
                    st.write("• เป็นเงินจริงที่โครงการได้รับ")
                    st.write("• สะท้อนความคืบหน้าที่แท้จริง")
                    st.write("• ไม่มีการขึ้นลง (Cumulative)")
                    st.write("• ตรงกับ Cash Flow จริง")
                    st.write("")
                    st.write("**🎯 สูตร:** Certificate Cumulative / Contract Value × 100%")
                
                # แสดงกราฟเปรียบเทียบวิธีการคำนวณ
                try:
                    progress_chart = dashboard.create_progress_comparison_chart(selected_project)
                    st.plotly_chart(progress_chart, use_container_width=True)
                    
                    # แสดงข้อมูลตัวเลข
                    progress_data = dashboard.analyze_progress_data(selected_project)
                    if not progress_data.empty:
                        st.write("**📊 ตารางเปรียบเทียบวิธีการคำนวณ:**")
                        
                        # เลือก columns ที่มีข้อมูล
                        display_cols = ['month']
                        col_mapping = {'month': 'เดือน'}
                        
                        if progress_data['progress_original'].sum() > 0:
                            display_cols.append('progress_original')
                            col_mapping['progress_original'] = 'Mockup (%)'
                            
                        if progress_data['progress_from_certificate'].sum() > 0:
                            display_cols.append('progress_from_certificate') 
                            col_mapping['progress_from_certificate'] = 'Certificate (%)'
                            
                        if progress_data['progress_from_submit'].sum() > 0:
                            display_cols.append('progress_from_submit')
                            col_mapping['progress_from_submit'] = 'Submit (%)'
                            
                        display_cols.append('progress_s_curve')
                        col_mapping['progress_s_curve'] = 'S-Curve (%)'
                        
                        comparison_df = progress_data[display_cols].round(1)
                        comparison_df = comparison_df.rename(columns=col_mapping)
                        st.dataframe(comparison_df, use_container_width=True)
                        
                        # สรุปวิธีที่ใช้
                        if progress_data['progress_from_certificate'].sum() > 0:
                            st.success("✅ **ใช้ Certificate Method** - วิธีที่แม่นยำที่สุด")
                        elif progress_data['progress_from_submit'].sum() > 0:
                            st.info("📊 **ใช้ Submit Method** - วิธีที่ดีรองลงมา")
                        else:
                            st.warning("⚠️ **ใช้ S-Curve Method** - วิธีจำลองมาตรฐาน")
                    
                except Exception as e:
                    st.error(f"Error creating progress analysis: {e}")
            
            # Raw Data Preview
            with st.expander("🔍 ดูข้อมูลดิบ"):
                project_raw_data = dashboard.df[dashboard.df['project_id'] == selected_project]
                st.write(f"📊 Records สำหรับ {selected_project}: {len(project_raw_data)}")
                st.write("**Columns ที่มี:**", list(project_raw_data.columns))
                st.dataframe(project_raw_data.head(10))
            
            # Export Options
            st.markdown("---")
            st.subheader("💾 Export Options")
            
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                if st.button("📊 Export Charts as HTML"):
                    # สร้าง HTML report
                    html_content = f"""
                    <html>
                    <head><title>Project Analysis Report - {selected_project}</title></head>
                    <body>
                    <h1>Project Analysis Report</h1>
                    <h2>Project: {selected_project}</h2>
                    <h3>KPIs:</h3>
                    <ul>
                    {''.join([f'<li>{k}: {v}</li>' for k, v in kpis.items()])}
                    </ul>
                    </body>
                    </html>
                    """
                    
                    st.download_button(
                        "⬇️ Download HTML Report",
                        html_content,
                        f"project_report_{selected_project}.html",
                        "text/html"
                    )
            
            with export_col2:
                if st.button("📊 Export Table as CSV"):
                    try:
                        scode_table = dashboard.create_scode_table(selected_project)
                        if not scode_table.empty:
                            csv_data = scode_table.to_csv(index=False)
                            st.download_button(
                                "⬇️ Download CSV",
                                csv_data,
                                f"scode_analysis_{selected_project}.csv",
                                "text/csv"
                            )
                        else:
                            st.warning("ไม่มีข้อมูลให้ export")
                    except Exception as e:
                        st.error(f"Error exporting: {e}")
                        
        except Exception as e:
            st.error(f"❌ Error processing project {selected_project}: {e}")
            st.info("💡 ลองเลือกโครงการอื่น หรือตรวจสอบข้อมูล")
    
    # Debug Information
    with st.expander("🛠️ Debug Information"):
        if dashboard.df is not None:
            st.write("**ข้อมูลที่โหลด:**")
            st.write(f"• Shape: {dashboard.df.shape}")
            st.write(f"• Projects: {dashboard.df['project_id'].nunique()}")
            st.write(f"• Months: {sorted(dashboard.df['month'].unique())}")
            st.write("**Columns:**", dashboard.df.columns.tolist())
            
            st.write("**Sample Data:**")
            st.dataframe(dashboard.df.head(3))

# Standalone version
def create_standalone_charts(project_id='PRJ001'):
    """สร้างกราฟแบบ standalone สำหรับใช้ใน notebook"""
    dashboard = ProjectAnalysisDashboard()
    
    if dashboard.df is None:
        print("❌ ไม่สามารถโหลดข้อมูลได้")
        return None
    
    print(f"📊 Creating charts for project: {project_id}")
    
    # สร้างกราฟ
    chart1 = dashboard.create_chart_1(project_id)
    chart2 = dashboard.create_chart_2(project_id)
    
    # สร้างตาราง
    table = dashboard.create_scode_table(project_id)
    
    # คำนวณ KPIs
    kpis, interpretations, _ = dashboard.calculate_project_kpis(project_id)
    
    # แสดงผล
    chart1.show()
    chart2.show()
    
    print("\n📋 S-Code Analysis Table:")
    print(table.to_string(index=False))
    
    print(f"\n📈 Project KPIs:")
    for key, value in kpis.items():
        print(f"• {key}: {value}")
    
    return chart1, chart2, table, kpis

# Simple test and data checker
def check_data_compatibility():
    """ตรวจสอบความพร้อมของข้อมูล"""
    try:
        df = pd.read_csv('data/processed/master_data.csv')
        print(f"✅ โหลดข้อมูลสำเร็จ: {len(df)} records")
        
        # ตรวจสอบ columns ที่จำเป็น
        required_columns = ['project_id', 'month', 'total_budget', 'total_actual', 'progress_percentage']
        missing_required = [col for col in required_columns if col not in df.columns]
        
        if missing_required:
            print(f"❌ ขาด columns จำเป็น: {missing_required}")
            return False
        
        print(f"✅ Columns จำเป็นครบ: {required_columns}")
        
        # ตรวจสอบ EVM columns
        evm_columns = ['bcwp', 'acwp', 'bcws', 'cpi', 'spi', 'eac', 'vac']
        available_evm = [col for col in evm_columns if col in df.columns]
        missing_evm = [col for col in evm_columns if col not in df.columns]
        
        print(f"✅ EVM columns ที่มี: {available_evm}")
        if missing_evm:
            print(f"⚠️ EVM columns ที่ขาด: {missing_evm} (จะคำนวณให้อัตโนมัติ)")
        
        # ตรวจสอบ Progress Payment columns (สำคัญ!)
        payment_columns = ['progress_submit', 'certificate', 'submit_balance']
        available_payment = [col for col in payment_columns if col in df.columns]
        
        print(f"\n📊 Progress Payment Analysis:")
        if available_payment:
            print(f"✅ Payment columns ที่มี: {available_payment}")
            
            for col in available_payment:
                total_amount = df[col].sum()
                non_zero_count = (df[col] > 0).sum()
                print(f"   • {col}: {total_amount:,.0f} บาท ({non_zero_count} records มีข้อมูล)")
                
            # ตรวจสอบว่าจะใช้วิธีไหนในการคำนวณ progress
            if 'certificate' in available_payment and df['certificate'].sum() > 0:
                print(f"🎯 จะใช้ Certificate Method ในการคำนวณ Progress (แม่นยำสุด)")
            elif 'progress_submit' in available_payment and df['progress_submit'].sum() > 0:
                print(f"📊 จะใช้ Submit Method ในการคำนวณ Progress (ดีรองลงมา)")
            else:
                print(f"📈 จะใช้ BCWP/Budget Method ในการคำนวณ Progress")
        else:
            print(f"⚠️ ไม่มี Payment columns: {payment_columns}")
            print(f"📈 จะใช้ S-Curve Model ในการคำนวณ Progress")
        
        # ตรวจสอบ projects
        projects = df['project_id'].unique()
        print(f"\n✅ Projects ที่มี: {list(projects)}")
        
        # ตรวจสอบ months
        months = sorted(df['month'].unique())
        print(f"✅ Months ที่มี: {months}")
        
        # Sample progress analysis สำหรับ project แรก
        if len(projects) > 0:
            sample_project = projects[0]
            project_data = df[df['project_id'] == sample_project]
            
            print(f"\n📊 ตัวอย่างข้อมูล Progress สำหรับ {sample_project}:")
            
            monthly_summary = project_data.groupby('month').agg({
                'progress_percentage': 'mean',
                'certificate': 'sum' if 'certificate' in df.columns else lambda x: 0,
                'progress_submit': 'sum' if 'progress_submit' in df.columns else lambda x: 0,
                'total_actual': 'sum'
            }).round(1)
            
            for _, row in monthly_summary.head(5).iterrows():
                month = int(row.name)
                progress = row['progress_percentage']
                cert = row.get('certificate', 0)
                submit = row.get('progress_submit', 0)
                actual = row['total_actual']
                
                print(f"   เดือน {month}: Progress {progress:.1f}%, Certificate {cert:,.0f}, Submit {submit:,.0f}, Actual {actual:,.0f}")
        
        return True
        
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์: data/processed/master_data.csv")
        print("💡 รัน ETL script ก่อน: python etl_script.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Standalone version with data checking
def create_charts_with_data_check(project_id='PRJ001'):
    """สร้างกราฟพร้อมตรวจสอบข้อมูล"""
    print("🔍 ตรวจสอบข้อมูล...")
    
    if not check_data_compatibility():
        return None
    
    print(f"\n📊 สร้างกราฟสำหรับโครงการ: {project_id}")
    
    try:
        dashboard = ProjectAnalysisDashboard()
        
        if dashboard.df is None:
            print("❌ ไม่สามารถโหลด dashboard ได้")
            return None
        
        # ตรวจสอบโครงการ
        available_projects = dashboard.get_project_list()
        if project_id not in available_projects:
            print(f"❌ ไม่พบโครงการ {project_id}")
            print(f"💡 โครงการที่มี: {available_projects}")
            project_id = available_projects[0]
            print(f"📊 ใช้โครงการแทน: {project_id}")
        
        # สร้างกราฟ
        chart1 = dashboard.create_chart_1(project_id)
        chart2 = dashboard.create_chart_2(project_id)
        
        # สร้างตาราง
        table = dashboard.create_scode_table(project_id)
        
        # คำนวณ KPIs
        kpis, interpretations, _ = dashboard.calculate_project_kpis(project_id)
        
        # แสดงผล
        print(f"\n🎯 KPIs สำหรับ {project_id}:")
        for key, value in kpis.items():
            interp = interpretations.get(key.split()[0], "")
            print(f"• {key}: {value} {interp}")
        
        print(f"\n📋 S-Code Table:")
        if not table.empty:
            print(table.to_string(index=False))
        else:
            print("⚠️ ไม่มีข้อมูล S-Code")
        
        # แสดงกราฟ
        chart1.show()
        chart2.show()
        
        return chart1, chart2, table, kpis
        
    except Exception as e:
        print(f"❌ Error สร้างกราฟ: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        # รัน data check
        check_data_compatibility()
    elif len(sys.argv) > 1 and sys.argv[1] == 'test':
        # รัน test charts
        create_charts_with_data_check()
    else:
        # รัน Streamlit app
        main()
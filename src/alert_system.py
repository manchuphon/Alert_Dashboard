"""
Simple Alert System - ระบบแจ้งเตือนแบบง่าย ไม่ต้อง dependencies เยอะ
รันได้ทันทีด้วย pandas และ numpy เท่านั้น
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SimpleAlert:
    """Alert object แบบง่าย"""
    project_id: str
    project_name: str
    alert_type: str
    severity: str  # Critical, High, Medium, Low
    message: str
    actual_value: float
    threshold: float
    variance: float
    details: Dict

class SimpleAlertEngine:
    """Alert Engine แบบง่าย"""
    
    def __init__(self, data_file='data/processed/master_data.csv'):
        self.data_file = data_file
        self.alerts = []
        
        # Alert thresholds
        self.thresholds = {
            'cost_overrun': 100,      # เกิน 100% ของงบประมาณ
            'progress_lag': 150,      # cost/progress ratio > 150%
            'high_variance': 25,      # variance > 25%
            'low_efficiency': 40,     # efficiency < 40
            'schedule_delay': 20      # ล่าช้า > 20%
        }
        
    def load_data(self):
        """โหลดข้อมูล"""
        try:
            print(f"📊 กำลังโหลดข้อมูลจาก {self.data_file}...")
            self.df = pd.read_csv(self.data_file)
            print(f"✅ โหลดข้อมูลสำเร็จ: {len(self.df):,} records")
            return True
        except FileNotFoundError:
            print(f"❌ ไม่พบไฟล์: {self.data_file}")
            print("💡 ตรวจสอบว่าได้รัน ETL script แล้วหรือยัง")
            return False
        except Exception as e:
            print(f"❌ Error loading data: {str(e)}")
            return False
    
    def check_cost_overrun(self, row):
        """ตรวจสอบการเกินงบประมาณ"""
        if row['total_budget'] == 0:
            return None
            
        utilization = (row['total_actual'] / row['total_budget']) * 100
        
        if utilization > self.thresholds['cost_overrun']:
            severity = 'Critical' if utilization > 130 else 'High' if utilization > 115 else 'Medium'
            
            return SimpleAlert(
                project_id=row['project_id'],
                project_name=row.get('project_name', f"Project {row['project_id']}"),
                alert_type='cost_overrun',
                severity=severity,
                message=f"เกินงบประมาณ {utilization:.1f}% (งบ: {row['total_budget']:,.0f}, ใช้: {row['total_actual']:,.0f})",
                actual_value=utilization,
                threshold=self.thresholds['cost_overrun'],
                variance=utilization - self.thresholds['cost_overrun'],
                details={
                    'cost_code': f"{row['g_code']}-{row['s_code']}",
                    'month': row['month'],
                    'budget': row['total_budget'],
                    'actual': row['total_actual'],
                    'progress': row['progress_percentage']
                }
            )
        return None
    
    def check_progress_lag(self, row):
        """ตรวจสอบความคืบหน้าล่าช้า"""
        if row['progress_percentage'] == 0 or row['total_budget'] == 0:
            return None
            
        # คำนวณ ratio ของต้นทุน vs ความคืบหน้า
        cost_ratio = (row['total_actual'] / (row['progress_percentage'] * row['total_budget'] / 100)) * 100
        
        if cost_ratio > self.thresholds['progress_lag']:
            severity = 'Critical' if cost_ratio > 250 else 'High' if cost_ratio > 200 else 'Medium'
            
            return SimpleAlert(
                project_id=row['project_id'],
                project_name=row.get('project_name', f"Project {row['project_id']}"),
                alert_type='progress_lag',
                severity=severity,
                message=f"ความคืบหน้าล่าช้า - ใช้เงิน {cost_ratio:.1f}% เทียบกับความคืบหน้า",
                actual_value=cost_ratio,
                threshold=self.thresholds['progress_lag'],
                variance=cost_ratio - self.thresholds['progress_lag'],
                details={
                    'cost_code': f"{row['g_code']}-{row['s_code']}",
                    'month': row['month'],
                    'progress': row['progress_percentage'],
                    'cost_ratio': cost_ratio
                }
            )
        return None
    
    def check_schedule_delay(self, row):
        """ตรวจสอบการล่าช้าจากแผนงาน"""
        # สมมติแผนงาน linear: เดือนที่ 6 ควรเสร็จ 50%
        expected_progress = (row['month'] / 12) * 100
        delay = expected_progress - row['progress_percentage']
        
        if delay > self.thresholds['schedule_delay']:
            severity = 'Critical' if delay > 50 else 'High' if delay > 35 else 'Medium'
            
            return SimpleAlert(
                project_id=row['project_id'],
                project_name=row.get('project_name', f"Project {row['project_id']}"),
                alert_type='schedule_delay',
                severity=severity,
                message=f"ล่าช้าจากแผน {delay:.1f}% (ควรอยู่ที่ {expected_progress:.1f}%, อยู่ที่ {row['progress_percentage']:.1f}%)",
                actual_value=delay,
                threshold=self.thresholds['schedule_delay'],
                variance=delay - self.thresholds['schedule_delay'],
                details={
                    'cost_code': f"{row['g_code']}-{row['s_code']}",
                    'month': row['month'],
                    'expected_progress': expected_progress,
                    'actual_progress': row['progress_percentage']
                }
            )
        return None
    
    def check_efficiency(self, row):
        """ตรวจสอบประสิทธิภาพ"""
        if 'efficiency_score' not in row or pd.isna(row['efficiency_score']):
            return None
            
        efficiency = row['efficiency_score']
        
        if efficiency < self.thresholds['low_efficiency']:
            severity = 'Critical' if efficiency < 20 else 'High' if efficiency < 30 else 'Medium'
            
            return SimpleAlert(
                project_id=row['project_id'],
                project_name=row.get('project_name', f"Project {row['project_id']}"),
                alert_type='low_efficiency',
                severity=severity,
                message=f"ประสิทธิภาพต่ำ {efficiency:.1f} คะแนน (ต่ำกว่า {self.thresholds['low_efficiency']})",
                actual_value=efficiency,
                threshold=self.thresholds['low_efficiency'],
                variance=self.thresholds['low_efficiency'] - efficiency,
                details={
                    'cost_code': f"{row['g_code']}-{row['s_code']}",
                    'month': row['month'],
                    'efficiency_score': efficiency
                }
            )
        return None
    
    def evaluate_all_alerts(self):
        """ประเมิน alerts ทั้งหมด"""
        if not hasattr(self, 'df'):
            if not self.load_data():
                return []
        
        print("🔍 กำลังประเมิน alerts...")
        
        alerts = []
        check_functions = [
            self.check_cost_overrun,
            self.check_progress_lag,
            self.check_schedule_delay,
            self.check_efficiency
        ]
        
        for _, row in self.df.iterrows():
            for check_func in check_functions:
                try:
                    alert = check_func(row)
                    if alert:
                        alerts.append(alert)
                except Exception as e:
                    print(f"⚠️ Error checking {check_func.__name__} for {row['project_id']}: {e}")
        
        self.alerts = alerts
        print(f"🚨 พบ {len(alerts)} alerts")
        return alerts
    
    def get_alert_summary(self):
        """สรุป alerts"""
        if not self.alerts:
            return {"total": 0}
        
        summary = {
            "total": len(self.alerts),
            "by_severity": {},
            "by_type": {},
            "by_project": {}
        }
        
        for alert in self.alerts:
            # By severity
            severity = alert.severity
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # By type
            alert_type = alert.alert_type
            summary["by_type"][alert_type] = summary["by_type"].get(alert_type, 0) + 1
            
            # By project
            project = alert.project_id
            summary["by_project"][project] = summary["by_project"].get(project, 0) + 1
        
        return summary
    
    def print_alerts(self, limit=20):
        """แสดง alerts ใน console"""
        if not self.alerts:
            print("✅ ไม่พบ alerts")
            return
        
        # เรียงตาม severity
        severity_order = ['Critical', 'High', 'Medium', 'Low']
        sorted_alerts = sorted(self.alerts, key=lambda x: severity_order.index(x.severity))
        
        print(f"\n{'='*80}")
        print(f"🚨 BUDGET ALERTS REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # Summary
        summary = self.get_alert_summary()
        print(f"📊 SUMMARY:")
        print(f"   Total Alerts: {summary['total']}")
        print(f"   By Severity: {summary['by_severity']}")
        print(f"   By Type: {summary['by_type']}")
        print(f"   Projects Affected: {len(summary['by_project'])}")
        
        print(f"\n{'='*80}")
        print(f"🔥 TOP {min(limit, len(sorted_alerts))} ALERTS:")
        print(f"{'='*80}")
        
        for i, alert in enumerate(sorted_alerts[:limit], 1):
            severity_emoji = {
                'Critical': '🔴',
                'High': '🟠', 
                'Medium': '🟡',
                'Low': '🟢'
            }.get(alert.severity, '⚠️')
            
            print(f"\n{i}. {severity_emoji} [{alert.severity}] {alert.alert_type.upper()}")
            print(f"   📁 {alert.project_name} ({alert.project_id})")
            print(f"   💬 {alert.message}")
            print(f"   📋 Cost Code: {alert.details.get('cost_code', 'N/A')} | Month: {alert.details.get('month', 'N/A')}")
            print(f"   📈 Current: {alert.actual_value:.1f} | Threshold: {alert.threshold:.1f} | Variance: {alert.variance:.1f}")
        
        if len(sorted_alerts) > limit:
            print(f"\n... และอีก {len(sorted_alerts) - limit} alerts")
        
        print(f"{'='*80}")
    
    def export_alerts_json(self, filename='alerts_report.json'):
        """Export alerts เป็น JSON"""
        if not self.alerts:
            print("ไม่มี alerts ให้ export")
            return
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_alert_summary(),
            'alerts': []
        }
        
        for alert in self.alerts:
            export_data['alerts'].append({
                'project_id': alert.project_id,
                'project_name': alert.project_name,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'actual_value': alert.actual_value,
                'threshold': alert.threshold,
                'variance': alert.variance,
                'details': alert.details
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Exported alerts to {filename}")
    
    def get_critical_projects(self):
        """ดึงโครงการที่มี critical alerts"""
        critical_alerts = [a for a in self.alerts if a.severity == 'Critical']
        projects = {}
        
        for alert in critical_alerts:
            project_id = alert.project_id
            if project_id not in projects:
                projects[project_id] = {
                    'project_name': alert.project_name,
                    'alerts': []
                }
            projects[project_id]['alerts'].append(alert)
        
        return projects

class SimpleAlertManager:
    """Alert Manager แบบง่าย"""
    
    def __init__(self):
        self.engine = SimpleAlertEngine()
    
    def run_check(self):
        """รัน alert check"""
        print("🚨 เริ่ม Simple Alert Check...")
        alerts = self.engine.evaluate_all_alerts()
        return alerts
    
    def show_dashboard(self):
        """แสดง dashboard ใน console"""
        alerts = self.engine.alerts
        summary = self.engine.get_alert_summary()
        
        print(f"\n{'='*60}")
        print(f"📊 ALERT DASHBOARD")
        print(f"{'='*60}")
        
        if summary['total'] == 0:
            print("✅ ไม่มี alerts - ทุกโครงการอยู่ในสถานะปกติ")
            return
        
        # Overall status
        critical_count = summary['by_severity'].get('Critical', 0)
        high_count = summary['by_severity'].get('High', 0)
        
        if critical_count > 0:
            status = "🔴 CRITICAL"
        elif high_count > 0:
            status = "🟠 HIGH RISK"
        else:
            status = "🟡 ATTENTION NEEDED"
        
        print(f"🚨 Overall Status: {status}")
        print(f"📊 Total Alerts: {summary['total']}")
        print(f"🔥 Critical: {critical_count} | High: {high_count} | Medium: {summary['by_severity'].get('Medium', 0)}")
        
        # Top projects with issues
        print(f"\n📋 Top Projects with Most Alerts:")
        project_counts = summary['by_project']
        top_projects = sorted(project_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for project_id, count in top_projects:
            print(f"   • {project_id}: {count} alerts")
        
        # Alert types breakdown
        print(f"\n📈 Alert Types:")
        for alert_type, count in summary['by_type'].items():
            print(f"   • {alert_type.replace('_', ' ').title()}: {count}")
        
        print(f"{'='*60}")

# === MAIN EXECUTION ===
def main():
    """Main function สำหรับรัน alert system"""
    print("🚨 Simple AI Budget Alert System")
    print("=" * 60)
    
    # สร้าง alert manager
    alert_manager = SimpleAlertManager()
    
    try:
        # รัน alert check
        alerts = alert_manager.run_check()
        
        if alerts:
            # แสดง dashboard
            alert_manager.show_dashboard()
            
            # แสดงรายละเอียด alerts
            alert_manager.engine.print_alerts(limit=10)
            
            # Export JSON
            alert_manager.engine.export_alerts_json()
            
            # แสดง critical projects
            critical_projects = alert_manager.engine.get_critical_projects()
            if critical_projects:
                print(f"\n🚨 CRITICAL PROJECTS REQUIRING IMMEDIATE ATTENTION:")
                for project_id, project_data in critical_projects.items():
                    print(f"   🔴 {project_data['project_name']} ({project_id})")
                    print(f"       {len(project_data['alerts'])} critical alerts")
        else:
            print("✅ เยี่ยม! ไม่พบ alerts - ทุกโครงการอยู่ในสถานะดี")
        
        # แนะนำการใช้งานต่อ
        print(f"\n💡 การใช้งานเพิ่มเติม:")
        print(f"   • ดู alerts ทั้งหมด: alert_manager.engine.print_alerts()")
        print(f"   • Export JSON: alert_manager.engine.export_alerts_json()")
        print(f"   • แก้ไข thresholds: alert_manager.engine.thresholds")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"💡 ตรวจสอบว่าไฟล์ data/processed/master_data.csv มีอยู่หรือไม่")

if __name__ == "__main__":
    main()
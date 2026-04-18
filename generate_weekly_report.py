#!/usr/bin/env python3
import requests
import json
import datetime
import os

MES_URL = "http://localhost:5000/api/mes"
PCS_URL = "http://localhost:5003/api/v1"
REPORT_DIR = "/home/ubuntu/manufacturing_emulator/reports"

def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def generate_report():
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    # Fetch MES data
    mes_status = fetch_data("http://localhost:5002/api/v1/status")
    mes_machines = fetch_data(f"{MES_URL}/machines") or []
    mes_work_orders = fetch_data(f"{MES_URL}/work-orders") or []
    mes_quality = fetch_data(f"{MES_URL}/quality-checks") or []
    
    # Fetch PCS data
    pcs_status = fetch_data(f"{PCS_URL}/status")
    pcs_machines = fetch_data(f"{PCS_URL}/machines/status") or {}
    pcs_alarms = fetch_data(f"{PCS_URL}/alarms") or []
    
    now = datetime.datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    report_path = os.path.join(REPORT_DIR, f"weekly_report_{report_date}.md")
    
    # Process MES Data
    active_wos = [wo for wo in mes_work_orders if wo.get('status') == 'in_progress']
    completed_wos = [wo for wo in mes_work_orders if wo.get('status') == 'completed']
    failed_quality = [q for q in mes_quality if q.get('status') == 'fail']
    
    # Process PCS Data
    running_machines = sum(1 for m in pcs_machines.values() if m.get('running'))
    active_alarms = [a for a in pcs_alarms if a.get('status') == 'active']
    
    with open(report_path, "w") as f:
        f.write(f"# Manufacturing System Weekly Report\n\n")
        f.write(f"**Date Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## System Health Status\n\n")
        f.write("| System | Status | Timestamp |\n")
        f.write("|---|---|---|\n")
        f.write(f"| MES | {'Online' if mes_status else 'Offline/Error'} | {now.strftime('%Y-%m-%d %H:%M:%S')} |\n")
        f.write(f"| PCS | {'Online' if pcs_status else 'Offline/Error'} | {now.strftime('%Y-%m-%d %H:%M:%S')} |\n\n")
        
        f.write("## Manufacturing Execution System (MES) Summary\n\n")
        f.write("The MES is responsible for orchestrating production. Below is the summary of work orders and quality metrics for the week.\n\n")
        f.write(f"- **Total Machines Registered:** {len(mes_machines)}\n")
        f.write(f"- **Active Work Orders:** {len(active_wos)}\n")
        f.write(f"- **Completed Work Orders:** {len(completed_wos)}\n")
        f.write(f"- **Total Quality Checks:** {len(mes_quality)}\n")
        f.write(f"- **Failed Quality Checks:** {len(failed_quality)}\n\n")
        
        if failed_quality:
            f.write("### Quality Check Failures\n\n")
            f.write("| Work Order | Parameter | Value | Status |\n")
            f.write("|---|---|---|---|\n")
            for q in failed_quality[:10]:
                f.write(f"| {q.get('work_order_number')} | {q.get('parameter')} | {q.get('value')} | {q.get('status')} |\n")
            f.write("\n")
            
        f.write("## Process Control System (PCS) Summary\n\n")
        f.write("The PCS monitors real-time machine telemetry and manages equipment alarms.\n\n")
        f.write(f"- **Machines Currently Running:** {running_machines} / {len(pcs_machines)}\n")
        f.write(f"- **Active Alarms:** {len(active_alarms)}\n\n")
        
        if active_alarms:
            f.write("### Active Equipment Alarms\n\n")
            f.write("| Machine ID | Alarm Code | Severity | Description | Time |\n")
            f.write("|---|---|---|---|---|\n")
            for a in active_alarms:
                time_str = a.get('start_time', '').split('.')[0].replace('T', ' ')
                f.write(f"| {a.get('machine_id')} | {a.get('alarm_code')} | {a.get('severity')} | {a.get('description')} | {time_str} |\n")
            f.write("\n")
            
        f.write("## Potential Errors & Anomalies\n\n")
        errors_found = False
        
        if not mes_status or not pcs_status:
            f.write("- **CRITICAL:** One or more core services are offline.\n")
            errors_found = True
            
        if len(failed_quality) > (len(mes_quality) * 0.1) and len(mes_quality) > 0:
            f.write(f"- **WARNING:** High quality failure rate detected ({(len(failed_quality)/len(mes_quality))*100:.1f}%).\n")
            errors_found = True
            
        if len([a for a in active_alarms if a.get('severity') == 'error']) > 0:
            f.write("- **ERROR:** Critical machine alarms are currently active and require immediate maintenance.\n")
            errors_found = True
            
        if not errors_found:
            f.write("No critical errors or anomalies detected during this reporting period.\n")
            
    print(f"Report generated successfully at: {report_path}")
    return report_path

if __name__ == "__main__":
    generate_report()

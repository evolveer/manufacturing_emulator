#!/usr/bin/env python3
"""
Diagnostic and Fix Script for Manufacturing Emulator System
This script diagnoses and fixes common issues with the manufacturing emulator system
"""

import os
import sys
import json
import requests
import subprocess
import time
import re
from pathlib import Path

# Configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
COMPONENTS = ["erp", "mes", "pcs", "interface"]
PORTS = {"erp": 5001, "mes": 5002, "pcs": 5003, "interface": 5000}
API_PATHS = {
    "erp": ["materials", "products", "production-plans"],
    "mes": ["work-orders", "machines", "schedule"],
    "pcs": ["machines/status", "alarms"]
}

class EmulatorDiagnostic:
    def __init__(self):
        self.issues_found = 0
        self.issues_fixed = 0
        self.log_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
    def run_diagnostics(self):
        """Run all diagnostic checks and fixes"""
        print("=" * 60)
        print("Manufacturing Emulator System Diagnostic Tool")
        print("=" * 60)
        print("\nRunning diagnostics...\n")
        
        self.check_processes()
        self.check_database_files()
        self.check_api_connectivity()
        self.check_cors_configuration()
        self.check_json_serialization()
        self.check_template_files()
        
        print("\n" + "=" * 60)
        print(f"Diagnostic Summary: {self.issues_found} issues found, {self.issues_fixed} issues fixed")
        print("=" * 60)
        
        if self.issues_fixed > 0:
            print("\nSome issues were fixed. Please restart the system with:")
            print("./stop.sh && ./start.sh")
        elif self.issues_found == 0:
            print("\nNo issues were detected with the basic configuration.")
            print("If you're still experiencing problems, please check the application logs for more details.")
        else:
            print("\nSome issues were detected but could not be automatically fixed.")
            print("Please review the diagnostic output above for manual steps.")
            
    def check_processes(self):
        """Check if all required processes are running"""
        print("\n[1/6] Checking system processes...")
        
        running_processes = {}
        for component in COMPONENTS:
            pid_file = os.path.join(self.log_dir, f"{component}.pid" if component != "interface" else "interface.pid")
            if os.path.exists(pid_file):
                try:
                    with open(pid_file, 'r') as f:
                        pid = f.read().strip()
                    
                    # Check if process is running
                    try:
                        os.kill(int(pid), 0)
                        running_processes[component] = True
                        print(f"  ✓ {component.upper()} process is running (PID: {pid})")
                    except (OSError, ProcessLookupError):
                        running_processes[component] = False
                        print(f"  ✗ {component.upper()} process is not running (PID file exists but process is dead)")
                        self.issues_found += 1
                except Exception as e:
                    running_processes[component] = False
                    print(f"  ✗ Error checking {component.upper()} process: {str(e)}")
                    self.issues_found += 1
            else:
                running_processes[component] = False
                print(f"  ✗ {component.upper()} process is not running (No PID file)")
                self.issues_found += 1
        
        if all(running_processes.values()):
            print("  All required processes are running.")
        else:
            print("  Some processes are not running. Try restarting the system with:")
            print("  ./stop.sh && ./start.sh")
    
    def check_database_files(self):
        """Check if database files exist and are initialized"""
        print("\n[2/6] Checking database files...")
        
        db_dir = os.path.join(BASE_DIR, "database", "database")
        os.makedirs(db_dir, exist_ok=True)
        
        db_files = ["erp.db", "mes.db", "pcs.db"]
        missing_dbs = []
        
        for db_file in db_files:
            db_path = os.path.join(db_dir, db_file)
            if os.path.exists(db_path):
                if os.path.getsize(db_path) > 0:
                    print(f"  ✓ Database file {db_file} exists and is not empty")
                else:
                    print(f"  ✗ Database file {db_file} exists but is empty")
                    missing_dbs.append(db_file)
                    self.issues_found += 1
            else:
                print(f"  ✗ Database file {db_file} does not exist")
                missing_dbs.append(db_file)
                self.issues_found += 1
        
        if missing_dbs:
            print("  Attempting to initialize missing databases...")
            init_db_path = os.path.join(BASE_DIR, "database", "init_db.py")
            
            if os.path.exists(init_db_path):
                try:
                    subprocess.run([sys.executable, init_db_path], check=True)
                    print("  ✓ Database initialization completed")
                    self.issues_fixed += 1
                except subprocess.CalledProcessError:
                    print("  ✗ Failed to initialize databases")
            else:
                print(f"  ✗ Database initialization script not found at {init_db_path}")
    
    def check_api_connectivity(self):
        """Check if APIs are accessible"""
        print("\n[3/6] Checking API connectivity...")
        
        api_issues = False
        
        for component, endpoints in API_PATHS.items():
            port = PORTS.get(component)
            if not port:
                continue
                
            base_url = f"http://localhost:{port}/api/v1"
            
            for endpoint in endpoints:
                url = f"{base_url}/{endpoint}"
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        print(f"  ✓ API endpoint {url} is accessible")
                    else:
                        print(f"  ✗ API endpoint {url} returned status code {response.status_code}")
                        api_issues = True
                        self.issues_found += 1
                except requests.RequestException:
                    print(f"  ✗ API endpoint {url} is not accessible")
                    api_issues = True
                    self.issues_found += 1
        
        if api_issues:
            print("  Some API endpoints are not accessible. This may cause dashboard loading issues.")
            print("  Check the component logs for more details:")
            for component in COMPONENTS:
                log_file = os.path.join(self.log_dir, f"{component}.log" if component != "interface" else "interface.log")
                if os.path.exists(log_file):
                    print(f"  - {log_file}")
    
    def check_cors_configuration(self):
        """Check and fix CORS configuration in API files"""
        print("\n[4/6] Checking CORS configuration...")
        
        cors_issues = False
        cors_fixed = False
        
        for component in ["erp", "mes", "pcs"]:
            api_file = os.path.join(BASE_DIR, component, "api.py")
            
            if not os.path.exists(api_file):
                print(f"  ✗ API file {api_file} does not exist")
                cors_issues = True
                continue
                
            with open(api_file, 'r') as f:
                content = f.read()
            
            if "Access-Control-Allow-Origin" not in content:
                print(f"  ✗ CORS headers not found in {component}/api.py")
                cors_issues = True
                self.issues_found += 1
                
                # Add CORS headers
                cors_code = """
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response
"""
                # Find a good place to insert the CORS code
                if "app = Flask" in content:
                    # Add after imports
                    import_end = content.rfind("import") + content[content.rfind("import"):].find("\n") + 1
                    new_content = content[:import_end] + "\n" + cors_code + content[import_end:]
                    
                    with open(api_file, 'w') as f:
                        f.write(new_content)
                    
                    print(f"  ✓ Added CORS headers to {component}/api.py")
                    cors_fixed = True
                    self.issues_fixed += 1
                else:
                    print(f"  ✗ Could not find a suitable place to add CORS headers in {component}/api.py")
            else:
                print(f"  ✓ CORS headers found in {component}/api.py")
        
        if cors_issues and not cors_fixed:
            print("  CORS issues were detected but could not be automatically fixed.")
            print("  You may need to manually add CORS headers to the API files.")
    
    def check_json_serialization(self):
        """Check and fix JSON serialization issues"""
        print("\n[5/6] Checking for JSON serialization issues...")
        
        serialization_issues = False
        
        for component in ["erp", "mes", "pcs"]:
            api_file = os.path.join(BASE_DIR, component, "api.py")
            
            if not os.path.exists(api_file):
                print(f"  ✗ API file {api_file} does not exist")
                serialization_issues = True
                continue
                
            with open(api_file, 'r') as f:
                content = f.read()
            
            # Look for Response objects being returned
            response_pattern = r'return\s+Response\s*\('
            if re.search(response_pattern, content):
                print(f"  ✗ Found potential JSON serialization issues in {component}/api.py")
                serialization_issues = True
                self.issues_found += 1
                
                # Replace Response objects with direct dictionary returns
                modified_content = re.sub(
                    r'return\s+Response\s*\(\s*json\.dumps\s*\(\s*(\{.*?\})\s*\)\s*,\s*mimetype\s*=\s*[\'"]application/json[\'"]\s*\)',
                    r'return \1',
                    content
                )
                
                if modified_content != content:
                    with open(api_file, 'w') as f:
                        f.write(modified_content)
                    
                    print(f"  ✓ Fixed JSON serialization issues in {component}/api.py")
                    self.issues_fixed += 1
                else:
                    print(f"  ✗ Could not automatically fix JSON serialization issues in {component}/api.py")
            else:
                print(f"  ✓ No obvious JSON serialization issues found in {component}/api.py")
    
    def check_template_files(self):
        """Check if template files exist"""
        print("\n[6/6] Checking template files...")
        
        template_dir = os.path.join(BASE_DIR, "common", "templates")
        os.makedirs(template_dir, exist_ok=True)
        
        template_files = ["index.html", "erp_dashboard.html", "mes_dashboard.html", "pcs_dashboard.html"]
        missing_templates = []
        
        for template_file in template_files:
            template_path = os.path.join(template_dir, template_file)
            if os.path.exists(template_path):
                print(f"  ✓ Template file {template_file} exists")
            else:
                print(f"  ✗ Template file {template_file} does not exist")
                missing_templates.append(template_file)
                self.issues_found += 1
        
        if missing_templates:
            print("  Missing template files may cause dashboard loading issues.")
            print("  Please make sure all template files are in the correct location:")
            print(f"  {template_dir}")

if __name__ == "__main__":
    diagnostic = EmulatorDiagnostic()
    diagnostic.run_diagnostics()

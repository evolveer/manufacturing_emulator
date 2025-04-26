#!/usr/bin/env python3
"""
JSON Serialization Fix Script for Manufacturing Emulator System
This script fixes JSON serialization issues in all API files
"""

import os
import re
import sys

def fix_json_serialization():
    """Fix JSON serialization issues in API files"""
    components = ["erp", "mes", "pcs"]
    fixed_files = 0
    
    for component in components:
        api_file = f"{component}/api.py"
        
        if not os.path.exists(api_file):
            print(f"Error: API file {api_file} not found")
            continue
        
        print(f"Checking {api_file} for JSON serialization issues...")
        
        # Read the file
        with open(api_file, 'r') as f:
            content = f.read()
        
        # Make a backup
        with open(f"{api_file}.bak", 'w') as f:
            f.write(content)
        
        # Fix pattern 1: Response objects with json.dumps
        pattern1 = r'return\s+Response\s*\(\s*json\.dumps\s*\(\s*(\{.*?\})\s*\)\s*,\s*mimetype\s*=\s*[\'"]application/json[\'"]\s*\)'
        if re.search(pattern1, content):
            content = re.sub(pattern1, r'return \1', content)
            print(f"  Fixed Response objects with json.dumps in {api_file}")
            fixed_files += 1
        
        # Fix pattern 2: Direct Response objects
        pattern2 = r'return\s+Response\s*\(\s*jsonify\s*\(\s*(.*?)\s*\)\s*\)'
        if re.search(pattern2, content):
            content = re.sub(pattern2, r'return \1', content)
            print(f"  Fixed Response objects with jsonify in {api_file}")
            fixed_files += 1
        
        # Fix pattern 3: Response objects with string content
        pattern3 = r'return\s+Response\s*\(\s*[\'"](.+?)[\'"]\s*,\s*mimetype\s*=\s*[\'"]application/json[\'"]\s*\)'
        if re.search(pattern3, content):
            content = re.sub(pattern3, r'return {"message": "\1"}', content)
            print(f"  Fixed Response objects with string content in {api_file}")
            fixed_files += 1
        
        # Fix pattern 4: make_response with jsonify
        pattern4 = r'return\s+make_response\s*\(\s*jsonify\s*\(\s*(.*?)\s*\)\s*\)'
        if re.search(pattern4, content):
            content = re.sub(pattern4, r'return \1', content)
            print(f"  Fixed make_response with jsonify in {api_file}")
            fixed_files += 1
        
        # Write the modified content back
        with open(api_file, 'w') as f:
            f.write(content)
    
    if fixed_files > 0:
        print(f"\nFixed JSON serialization issues in {fixed_files} files.")
        print("Please restart the system to apply the changes.")
    else:
        print("\nNo obvious JSON serialization issues found.")
        print("The issue might be in a specific API endpoint or in the interface code.")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    fix_json_serialization()

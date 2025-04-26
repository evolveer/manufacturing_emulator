#!/usr/bin/env python3
"""
ERP API Extension for Master Data Management
This module extends the ERP API to serve the master data management interface
"""

import os
import sys
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing ERP API components
from erp.api import app, api
from erp.services import MaterialService, ProductService, ProductionPlanService

# Enable CORS
CORS(app)

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# Serve master data management interface
@app.route('/master_data')
def master_data_page():
    return render_template('master_data.html')

# Serve documentation
@app.route('/docs/<path:path>')
def send_docs(path):
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
    return send_from_directory(docs_dir, path)

# Redirect root to master data page
@app.route('/')
def index():
    return render_template('master_data.html')

if __name__ == '__main__':
    # Create template directory if it doesn't exist
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    # Create static directory if it doesn't exist
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=5001, debug=True)

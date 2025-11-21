"""
System Interface Module
Provides a unified interface for operating and monitoring the integrated manufacturing system
"""
import os
import sys
import time
import json
import logging
import threading
import datetime
import requests
import yaml
import flask
from flask import Flask, request, jsonify, render_template, send_from_directory
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'interface.log'))
    ]
)

logger = logging.getLogger('system_interface')

# Create Flask app
app = Flask(
    __name__, 
    template_folder=os.path.join(project_root, 'common', 'templates'),
    static_folder=os.path.join(project_root, 'common', 'static')
)

# Load configuration
def load_config():
    """Load configuration from file"""
    config_path = os.path.join(project_root, 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# System URLs
erp_url = f"http://{config['erp']['host']}:{config['erp']['port']}/api/{config['erp']['api_version']}"
mes_url = f"http://{config['mes']['host']}:{config['mes']['port']}/api/{config['mes']['api_version']}"
pcs_url = f"http://{config['pcs']['host']}:{config['pcs']['port']}/api/{config['pcs']['api_version']}"

# System status cache
system_status = {
    'erp': {'status': 'unknown', 'last_check': None},
    'mes': {'status': 'unknown', 'last_check': None},
    'pcs': {'status': 'unknown', 'last_check': None},
    'sync': {'status': 'unknown', 'last_check': None}
}

# Status check thread
status_thread = None
stop_event = threading.Event()

def check_component_status(component, port):
    try:
        # Try proper /api/v1/status endpoint
        response = requests.get(f"http://localhost:{port}/api/v1/status", timeout=1)
        if response.status_code == 200:
            return 'online'
        elif 500 <= response.status_code < 600:
            return 'error'
        else:
            return 'unknown'
    except requests.exceptions.RequestException:
        try:
            # Fallback - check if port is open
            response = requests.get(f"http://localhost:{port}/", timeout=1)
            return 'unknown'  # It's responding but not from the right endpoint
        except requests.exceptions.RequestException:
            return 'offline'

        
        

def check_system_status():
    """Update the global system status dictionary"""
    system_status['erp']['status'] = check_component_status('erp', config['erp']['port'])
    system_status['erp']['last_check'] = datetime.datetime.utcnow().isoformat()

    system_status['mes']['status'] = check_component_status('mes', config['mes']['port'])
    system_status['mes']['last_check'] = datetime.datetime.utcnow().isoformat()

    system_status['pcs']['status'] = check_component_status('pcs', config['pcs']['port'])
    system_status['pcs']['last_check'] = datetime.datetime.utcnow().isoformat()

    system_status['sync']['status'] = check_component_status('sync', config['interface']['port'])
    system_status['sync']['last_check'] = datetime.datetime.utcnow().isoformat()

def run_status_polling():
    """Run system status checks in a loop"""
    while not stop_event.is_set():
        check_system_status()
        time.sleep(5)  # Check every 5 seconds
        
def start_status_thread():
    """Start the status check thread"""
    global status_thread, stop_event
    
    if status_thread is None or not status_thread.is_alive():
        stop_event.clear()
        status_thread = threading.Thread(target=run_status_polling)
        status_thread.daemon = True
        status_thread.start()
        logger.info("Status check thread started")

def stop_status_thread():
    """Stop the status check thread"""
    global status_thread, stop_event
    
    if status_thread and status_thread.is_alive():
        stop_event.set()
        status_thread.join(timeout=5)
        status_thread = None
        logger.info("Status check thread stopped")

# Start status thread on startup
start_status_thread()

# Web interface routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/erp')
def erp_dashboard():
    """ERP dashboard page"""
    return render_template('erp_dashboard.html')

@app.route('/mes')
def mes_dashboard():
    """MES dashboard page"""
    return render_template('mes_dashboard.html')

@app.route('/pcs')
def pcs_dashboard():
    """PCS dashboard page"""
    return render_template('pcs_dashboard.html')

@app.route('/monitoring')
def monitoring():
    """System monitoring page"""
    return render_template('monitoring.html')

@app.route('/order-workflow')
def order_workflow():
    """Order processing workflow page"""
    return render_template('order_workflow.html')

# API routes
@app.route('/api/status')
def api_status():
    """Get status of all systems"""
    return jsonify(system_status)

@app.route('/api/v1/status')
def api_v1_status():
    return jsonify({"status": "ok", "component": "sync"})


# ERP API proxy routes
@app.route('/api/erp/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def erp_api_proxy(subpath):
    """Proxy requests to ERP API"""
    url = f"{erp_url}/{subpath}"
    
    try:
        if request.method == 'GET':
            response = requests.get(url, params=request.args)
        elif request.method == 'POST':
            response = requests.post(url, json=request.get_json())
        elif request.method == 'PUT':
            response = requests.put(url, json=request.get_json())
        elif request.method == 'DELETE':
            response = requests.delete(url)
        else:
            return jsonify({'error': 'Method not allowed'}), 405
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error proxying request to ERP API: {str(e)}")
        return jsonify({'error': str(e)}), 500

# MES API proxy routes
@app.route('/api/mes/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mes_api_proxy(subpath):
    """Proxy requests to MES API"""
    url = f"{mes_url}/{subpath}"
    payload = request.get_json(silent=True)
    
    try:
        if request.method == 'GET':
            response = requests.get(url, params=request.args)
        elif request.method == 'POST':
            response = requests.post(url, json=payload) if payload is not None else requests.post(url)
        elif request.method == 'PUT':
            response = requests.put(url, json=payload) if payload is not None else requests.put(url)
        elif request.method == 'DELETE':
            response = requests.delete(url)
        else:
            return jsonify({'error': 'Method not allowed'}), 405
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error proxying request to MES API: {str(e)}")
        return jsonify({'error': str(e)}), 500

# PCS API proxy routes
@app.route('/api/pcs/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def pcs_api_proxy(subpath):
    """Proxy requests to PCS API"""
    url = f"{pcs_url}/{subpath}"
    payload = request.get_json(silent=True)
    
    try:
        if request.method == 'GET':
            response = requests.get(url, params=request.args)
        elif request.method == 'POST':
            response = requests.post(url, json=payload) if payload is not None else requests.post(url)
        elif request.method == 'PUT':
            response = requests.put(url, json=payload) if payload is not None else requests.put(url)
        elif request.method == 'DELETE':
            response = requests.delete(url)
        else:
            return jsonify({'error': 'Method not allowed'}), 405
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f"Error proxying request to PCS API: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Integrated API routes
@app.route('/api/dashboard/summary')
def dashboard_summary():
    """Get summary data for dashboard"""
    try:
        # Get data from all systems
        summary = {
            'erp': {},
            'mes': {},
            'pcs': {},
            'system_status': system_status
        }
        
        # Get ERP summary data
        try:
            # Get orders
            response = requests.get(f"{erp_url}/orders")
            if response.status_code == 200:
                orders = response.json()
                summary['erp']['orders'] = {
                    'total': len(orders),
                    'pending': len([o for o in orders if o['status'] == 'pending']),
                    'in_progress': len([o for o in orders if o['status'] == 'in_progress']),
                    'completed': len([o for o in orders if o['status'] == 'completed'])
                }
            
            # Get materials
            response = requests.get(f"{erp_url}/materials")
            if response.status_code == 200:
                materials = response.json()
                summary['erp']['materials'] = {
                    'total': len(materials),
                    'low_stock': len([m for m in materials if m.get('quantity', 0) < m.get('min_quantity', 0)])
                }
            
            # Get production plans
            response = requests.get(f"{erp_url}/production-plans")
            if response.status_code == 200:
                plans = response.json()
                summary['erp']['production_plans'] = {
                    'total': len(plans),
                    'pending': len([p for p in plans if p['status'] == 'pending']),
                    'in_progress': len([p for p in plans if p['status'] == 'in_progress']),
                    'completed': len([p for p in plans if p['status'] == 'completed'])
                }
        except Exception as e:
            logger.error(f"Error getting ERP summary data: {str(e)}")
            summary['erp']['error'] = str(e)
        
        # Get MES summary data
        try:
            # Get work orders
            response = requests.get(f"{mes_url}/work-orders")
            if response.status_code == 200:
                work_orders = response.json()
                summary['mes']['work_orders'] = {
                    'total': len(work_orders),
                    'pending': len([wo for wo in work_orders if wo['status'] == 'pending']),
                    'in_progress': len([wo for wo in work_orders if wo['status'] == 'in_progress']),
                    'completed': len([wo for wo in work_orders if wo['status'] == 'completed'])
                }
            
            # Get machines
            response = requests.get(f"{mes_url}/machines")
            if response.status_code == 200:
                machines = response.json()
                summary['mes']['machines'] = {
                    'total': len(machines),
                    'available': len([m for m in machines if m['status'] == 'available']),
                    'running': len([m for m in machines if m['status'] == 'running']),
                    'error': len([m for m in machines if m['status'] == 'error'])
                }
            
            # Get quality checks
            response = requests.get(f"{mes_url}/quality-checks")
            if response.status_code == 200:
                checks = response.json()
                summary['mes']['quality_checks'] = {
                    'total': len(checks),
                    'pass': len([c for c in checks if c['result'] == 'pass']),
                    'fail': len([c for c in checks if c['result'] == 'fail']),
                    'warning': len([c for c in checks if c['result'] == 'warning'])
                }
        except Exception as e:
            logger.error(f"Error getting MES summary data: {str(e)}")
            summary['mes']['error'] = str(e)
        
        # Get PCS summary data
        try:
            # Get machine status
            response = requests.get(f"{pcs_url}/machines/status")
            if response.status_code == 200:
                machines_status = response.json()
                summary['pcs']['machines'] = {
                    'total': len(machines_status),
                    'running': len([m for m_id, m in machines_status.items() if m.get('running', False)]),
                    'idle': len([m for m_id, m in machines_status.items() if not m.get('running', False)])
                }
            
            # Get alarms
            response = requests.get(f"{pcs_url}/alarms")
            if response.status_code == 200:
                alarms = response.json()
                summary['pcs']['alarms'] = {
                    'total': len(alarms),
                    'active': len([a for a in alarms if a['status'] == 'active']),
                    'acknowledged': len([a for a in alarms if a['status'] == 'acknowledged']),
                    'resolved': len([a for a in alarms if a['status'] == 'resolved'])
                }
        except Exception as e:
            logger.error(f"Error getting PCS summary data: {str(e)}")
            summary['pcs']['error'] = str(e)
        
        return jsonify(summary)
    
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/production')
def dashboard_production():
    """Get production data for dashboard"""
    try:
        # Get data from MES and PCS
        production_data = {
            'work_orders': [],
            'machines': [],
            'production_counts': {},
            'quality_summary': {}
        }
        
        # Get active work orders from MES
        try:
            response = requests.get(f"{mes_url}/work-orders/active")
            if response.status_code == 200:
                production_data['work_orders'] = response.json()
        except Exception as e:
            logger.error(f"Error getting active work orders: {str(e)}")
        
        # Get machine status from PCS
        try:
            response = requests.get(f"{pcs_url}/machines/status")
            if response.status_code == 200:
                machines_status = response.json()
                production_data['machines'] = [
                    {
                        'machine_id': int(machine_id),
                        'status': status
                    }
                    for machine_id, status in machines_status.items()
                ]
        except Exception as e:
            logger.error(f"Error getting machine status: {str(e)}")
        
        # Get production counts for active work orders
        for work_order in production_data['work_orders']:
            try:
                response = requests.get(f"{mes_url}/work-orders/{work_order['id']}/production-summary")
                if response.status_code == 200:
                    production_data['production_counts'][work_order['id']] = response.json()
            except Exception as e:
                logger.error(f"Error getting production counts for work order {work_order['id']}: {str(e)}")
        
        # Get quality summary for active work orders
        for work_order in production_data['work_orders']:
            try:
                response = requests.get(f"{mes_url}/work-orders/{work_order['id']}/quality-summary")
                if response.status_code == 200:
                    production_data['quality_summary'][work_order['id']] = response.json()
            except Exception as e:
                logger.error(f"Error getting quality summary for work order {work_order['id']}: {str(e)}")
        
        return jsonify(production_data)
    
    except Exception as e:
        logger.error(f"Error getting production data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/inventory')
def dashboard_inventory():
    """Get inventory data for dashboard"""
    try:
        # Get data from ERP
        inventory_data = {
            'materials': [],
            'products': []
        }
        
        # Get materials from ERP
        try:
            response = requests.get(f"{erp_url}/materials")
            if response.status_code == 200:
                inventory_data['materials'] = response.json()
        except Exception as e:
            logger.error(f"Error getting materials: {str(e)}")
        
        # Get products from ERP
        try:
            response = requests.get(f"{erp_url}/products")
            if response.status_code == 200:
                inventory_data['products'] = response.json()
        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
        
        return jsonify(inventory_data)
    
    except Exception as e:
        logger.error(f"Error getting inventory data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/quality')
def dashboard_quality():
    """Get quality data for dashboard"""
    try:
        # Get data from MES and PCS
        quality_data = {
            'quality_checks': [],
            'alarms': []
        }
        
        # Get quality checks from MES
        try:
            response = requests.get(f"{mes_url}/quality-checks")
            if response.status_code == 200:
                quality_data['quality_checks'] = response.json()
        except Exception as e:
            logger.error(f"Error getting quality checks: {str(e)}")
        
        # Get alarms from PCS
        try:
            response = requests.get(f"{pcs_url}/alarms")
            if response.status_code == 200:
                quality_data['alarms'] = response.json()
        except Exception as e:
            logger.error(f"Error getting alarms: {str(e)}")
        
        return jsonify(quality_data)
    
    except Exception as e:
        logger.error(f"Error getting quality data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Data synchronization control
@app.route('/api/sync/start', methods=['POST'])
def start_sync():
    """Start data synchronization"""
    try:
        # Import data sync module
        from common.data_sync import DataSynchronizer, load_config
        
        # Create synchronizer
        config = load_config()
        synchronizer = DataSynchronizer(config)
        
        # Start synchronization
        synchronizer.start()
        
        # Store synchronizer in app context
        app.config['synchronizer'] = synchronizer
        
        return jsonify({'status': 'started'})
    
    except Exception as e:
        logger.error(f"Error starting data synchronization: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/stop', methods=['POST'])
def stop_sync():
    """Stop data synchronization"""
    try:
        # Get synchronizer from app context
        synchronizer = app.config.get('synchronizer')
        
        if synchronizer:
            # Stop synchronization
            synchronizer.stop()
            
            # Remove synchronizer from app context
            app.config.pop('synchronizer', None)
            
            return jsonify({'status': 'stopped'})
        else:
            return jsonify({'error': 'Synchronizer not found'}), 404
    
    except Exception as e:
        logger.error(f"Error stopping data synchronization: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/status')
def sync_status():
    """Get data synchronization status"""
    try:
        # Get synchronizer from app context
        synchronizer = app.config.get('synchronizer')
        
        if synchronizer:
            # Get status
            status = synchronizer.get_status()
            return jsonify(status)
        else:
            return jsonify({'running': False})
    
    except Exception as e:
        logger.error(f"Error getting data synchronization status: {str(e)}")
        return jsonify({'error': str(e)}), 500

# System control
@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Start all system components"""
    try:
        # Start ERP
        try:
            # Start ERP process
            import subprocess
            subprocess.Popen(
                ['python3', os.path.join(project_root, 'erp', 'main.py')],
                cwd=project_root
            )
            logger.info("ERP process started")
        except Exception as e:
            logger.error(f"Error starting ERP: {str(e)}")
        
        # Start MES
        try:
            # Start MES process
            import subprocess
            subprocess.Popen(
                ['python3', os.path.join(project_root, 'mes', 'main.py')],
                cwd=project_root
            )
            logger.info("MES process started")
        except Exception as e:
            logger.error(f"Error starting MES: {str(e)}")
        
        # Start PCS
        try:
            # Start PCS process
            import subprocess
            subprocess.Popen(
                ['python3', os.path.join(project_root, 'pcs', 'main.py')],
                cwd=project_root
            )
            logger.info("PCS process started")
        except Exception as e:
            logger.error(f"Error starting PCS: {str(e)}")
        
        # Wait for systems to start
        time.sleep(5)
        
        # Start data synchronization
        try:
            response = requests.post(f"http://{config['interface']['host']}:{config['interface']['port']}/api/sync/start")
            if response.status_code == 200:
                logger.info("Data synchronization started")
            else:
                logger.error(f"Error starting data synchronization: {response.text}")
        except Exception as e:
            logger.error(f"Error starting data synchronization: {str(e)}")
        
        return jsonify({'status': 'started'})
    
    except Exception as e:
        logger.error(f"Error starting system: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Stop all system components"""
    try:
        # Stop data synchronization
        try:
            response = requests.post(f"http://{config['interface']['host']}:{config['interface']['port']}/api/sync/stop")
            if response.status_code == 200:
                logger.info("Data synchronization stopped")
            else:
                logger.error(f"Error stopping data synchronization: {response.text}")
        except Exception as e:
            logger.error(f"Error stopping data synchronization: {str(e)}")
        
        # Stop ERP
        try:
            requests.post(f"http://{config['erp']['host']}:{config['erp']['port']}/shutdown")
            logger.info("ERP shutdown requested")
        except Exception as e:
            logger.error(f"Error stopping ERP: {str(e)}")
        
        # Stop MES
        try:
            requests.post(f"http://{config['mes']['host']}:{config['mes']['port']}/shutdown")
            logger.info("MES shutdown requested")
        except Exception as e:
            logger.error(f"Error stopping MES: {str(e)}")
        
        # Stop PCS
        try:
            requests.post(f"http://{config['pcs']['host']}:{config['pcs']['port']}/shutdown")
            logger.info("PCS shutdown requested")
        except Exception as e:
            logger.error(f"Error stopping PCS: {str(e)}")
        
        return jsonify({'status': 'stopped'})
    
    except Exception as e:
        logger.error(f"Error stopping system: {str(e)}")
        return jsonify({'error': str(e)}), 500

def run_app():
    """Run the Flask application"""
    host = config['interface']['host']
    port = config['interface']['port']
    app.run(host=host, port=port, debug=True)

if __name__ == "__main__":
    run_app()

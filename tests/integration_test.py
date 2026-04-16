"""
Integration Test Script
Tests the integrated manufacturing emulator system
"""
import os
import sys
import time
import json
import logging
import requests
import subprocess
import yaml
from pathlib import Path

# L1 fix: project_root must be the repo root (parent of tests/), not tests/ itself.
# The old code used Path(__file__).parent which resolved to tests/ and caused
# config.yaml to be looked up at tests/config.yaml (which does not exist).
tests_dir = Path(__file__).parent.absolute()
project_root = tests_dir.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(tests_dir, 'test_results.log'))
    ]
)

logger = logging.getLogger('integration_test')


def load_config():
    """Load configuration from the repo-root config.yaml.

    L1 fix: config path is now derived from project_root (repo root), not
    from the tests/ subdirectory.
    """
    config_path = os.path.join(project_root, 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


config = load_config()


def _build_url(section: str, path: str = '') -> str:
    """Build a service URL from config, with environment-variable override.

    L1 fix: allows Docker Compose or CI environments to override URLs via
    environment variables (e.g. ERP_URL, MES_URL, PCS_URL, INTERFACE_URL)
    without modifying config.yaml.

    The config host '0.0.0.0' (bind address) is automatically translated to
    'localhost' for client-side connections.
    """
    env_key = f"{section.upper()}_URL"
    env_override = os.environ.get(env_key)
    if env_override:
        return env_override.rstrip('/') + ('/' + path.lstrip('/') if path else '')
    host = config[section]['host']
    # '0.0.0.0' is a bind address; translate to 'localhost' for outbound calls
    if host == '0.0.0.0':
        host = 'localhost'
    port = config[section]['port']
    base = f"http://{host}:{port}"
    if 'api_version' in config[section]:
        base += f"/api/{config[section]['api_version']}"
    return base + ('/' + path.lstrip('/') if path else '')


# System URLs — derived from config.yaml with env-var override support
erp_url = _build_url('erp')
mes_url = _build_url('mes')
pcs_url = _build_url('pcs')
interface_url = f"http://{'localhost' if config['interface']['host'] == '0.0.0.0' else config['interface']['host']}:{config['interface']['port']}"

# Test results
test_results = {
    'total': 0,
    'passed': 0,
    'failed': 0,
    'tests': []
}

def start_system():
    """Start all system components"""
    logger.info("Starting system components...")
    
    # Start ERP
    erp_process = subprocess.Popen(
        ['python3', os.path.join(project_root, 'erp', 'main.py')],
        cwd=project_root
    )
    logger.info("ERP process started")
    
    # Start MES
    mes_process = subprocess.Popen(
        ['python3', os.path.join(project_root, 'mes', 'main.py')],
        cwd=project_root
    )
    logger.info("MES process started")
    
    # Start PCS
    pcs_process = subprocess.Popen(
        ['python3', os.path.join(project_root, 'pcs', 'main.py')],
        cwd=project_root
    )
    logger.info("PCS process started")
    
    # Start Interface
    interface_process = subprocess.Popen(
        ['python3', os.path.join(project_root, 'common', 'interface.py')],
        cwd=project_root
    )
    logger.info("Interface process started")
    
    # Wait for systems to start
    logger.info("Waiting for systems to start...")
    time.sleep(10)
    
    return {
        'erp': erp_process,
        'mes': mes_process,
        'pcs': pcs_process,
        'interface': interface_process
    }

def stop_system(processes):
    """Stop all system components"""
    logger.info("Stopping system components...")
    
    # Stop processes
    for name, process in processes.items():
        if process.poll() is None:  # Process is still running
            process.terminate()
            logger.info(f"{name.upper()} process terminated")
    
    # Wait for processes to stop
    time.sleep(5)
    
    # Force kill any remaining processes
    for name, process in processes.items():
        if process.poll() is None:  # Process is still running
            process.kill()
            logger.info(f"{name.upper()} process killed")

def run_test(test_name, test_func):
    """Run a test and record the result"""
    logger.info(f"Running test: {test_name}")
    test_results['total'] += 1
    
    start_time = time.time()
    try:
        result = test_func()
        end_time = time.time()
        duration = end_time - start_time
        
        if result:
            test_results['passed'] += 1
            status = 'PASSED'
        else:
            test_results['failed'] += 1
            status = 'FAILED'
        
        logger.info(f"Test {test_name}: {status} ({duration:.2f}s)")
        
        test_results['tests'].append({
            'name': test_name,
            'status': status,
            'duration': duration
        })
        
        return result
    
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        test_results['failed'] += 1
        status = 'ERROR'
        
        logger.error(f"Test {test_name}: {status} - {str(e)} ({duration:.2f}s)")
        
        test_results['tests'].append({
            'name': test_name,
            'status': status,
            'error': str(e),
            'duration': duration
        })
        
        return False

def test_system_availability():
    """Test if all system components are available"""
    try:
        # Check ERP
        response = requests.get(f"http://{config['erp']['host']}:{config['erp']['port']}/")
        erp_available = response.status_code == 200
        
        # Check MES
        response = requests.get(f"http://{config['mes']['host']}:{config['mes']['port']}/")
        mes_available = response.status_code == 200
        
        # Check PCS
        response = requests.get(f"http://{config['pcs']['host']}:{config['pcs']['port']}/")
        pcs_available = response.status_code == 200
        
        # Check Interface
        response = requests.get(interface_url)
        interface_available = response.status_code == 200
        
        all_available = erp_available and mes_available and pcs_available and interface_available
        
        if all_available:
            logger.info("All system components are available")
        else:
            logger.error(f"System availability: ERP={erp_available}, MES={mes_available}, PCS={pcs_available}, Interface={interface_available}")
        
        return all_available
    
    except Exception as e:
        logger.error(f"Error checking system availability: {str(e)}")
        return False

def test_erp_functionality():
    """Test basic ERP functionality"""
    try:
        # Create a material
        material_data = {
            'name': 'Test Plastic Resin',
            'description': 'Test material for integration testing',
            'unit': 'kg',
            'quantity': 1000,
            'min_quantity': 100,
            'cost': 5.0
        }
        
# To this:
        response = requests.post(f"{ERP_URL}/materials", json=material_data)
        if response.ok:
            result = response.json()
        else:
            self.logger.error(f"Failed to create material: {response.text}")
            return False
        
        material_id = material['id']
        logger.info(f"Created material with ID {material_id}")
        
        # Create a product
        product_data = {
            'name': 'Test Plastic Part',
            'description': 'Test product for integration testing',
            'unit': 'pcs'
        }
        
        response = requests.post(f"{erp_url}/products", json=product_data)
        if response.status_code != 201:
            logger.error(f"Failed to create product: {response.text}")
            return False
        
        product = response.json()
        product_id = product['id']
        logger.info(f"Created product with ID {product_id}")
        
        # Create a BOM
        bom_data = {
            'product_id': product_id,
            'materials': [
                {
                    'material_id': material_id,
                    'quantity': 0.5
                }
            ]
        }
        
        response = requests.post(f"{erp_url}/boms", json=bom_data)
        if response.status_code != 201:
            logger.error(f"Failed to create BOM: {response.text}")
            return False
        
        bom = response.json()
        logger.info(f"Created BOM for product {product_id}")
        
        # Create a production plan
        plan_data = {
            'product_id': product_id,
            'quantity': 100,
            'due_date': (time.time() + 86400) * 1000,  # Tomorrow
            'priority': 1,
            'status': 'pending'
        }
        
        response = requests.post(f"{erp_url}/production-plans", json=plan_data)
        if response.status_code != 201:
            logger.error(f"Failed to create production plan: {response.text}")
            return False
        
        plan = response.json()
        plan_id = plan['id']
        logger.info(f"Created production plan with ID {plan_id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing ERP functionality: {str(e)}")
        return False

def test_mes_functionality():
    """Test basic MES functionality"""
    try:
        # Create a machine
        machine_data = {
            'name': 'Test Injection Machine',
            'code': 'IM-TEST-01',
            'type': 'injection_molding',
            'status': 'available',
            'location': 'Test Area'
        }
        
        response = requests.post(f"{mes_url}/machines", json=machine_data)
        if response.status_code != 201:
            logger.error(f"Failed to create machine: {response.text}")
            return False
        
        machine = response.json()
        machine_id = machine['id']
        logger.info(f"Created machine with ID {machine_id}")
        
        # Get production plans from ERP
        response = requests.get(f"{erp_url}/production-plans")
        if response.status_code != 200:
            logger.error(f"Failed to get production plans: {response.text}")
            return False
        
        plans = response.json()
        if not plans:
            logger.error("No production plans found in ERP")
            return False
        
        plan_id = plans[0]['id']
        
        # Create work orders from production plan
        response = requests.post(f"{mes_url}/production-plans/{plan_id}/create-work-orders")
        if response.status_code != 201:
            logger.error(f"Failed to create work orders: {response.text}")
            return False
        
        work_orders = response.json()
        work_order_id = work_orders[0]['id']
        logger.info(f"Created work order with ID {work_order_id}")
        
        # Schedule work order on machine
        schedule_data = {
            'machine_id': machine_id,
            'work_order_id': work_order_id,
            'start_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'end_time': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() + 3600)),
            'status': 'scheduled'
        }
        
        response = requests.post(f"{mes_url}/schedule", json=schedule_data)
        if response.status_code != 201:
            logger.error(f"Failed to schedule work order: {response.text}")
            return False
        
        schedule = response.json()
        logger.info(f"Scheduled work order {work_order_id} on machine {machine_id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing MES functionality: {str(e)}")
        return False

def test_pcs_functionality():
    """Test basic PCS functionality"""
    try:
        # Create a machine in PCS
        response = requests.post(f"{pcs_url}/machines", json={'machine_id': 1})
        if response.status_code != 201:
            logger.error(f"Failed to create machine in PCS: {response.text}")
            return False
        
        logger.info("Created machine in PCS")
        
        # Get machine status
        response = requests.get(f"{pcs_url}/machines/1/status")
        if response.status_code != 200:
            logger.error(f"Failed to get machine status: {response.text}")
            return False
        
        status = response.json()
        logger.info(f"Machine status: {status}")
        
        # Start machine
        response = requests.post(f"{pcs_url}/machines/1/start", json={'work_order_id': 1})
        if response.status_code != 200:
            logger.error(f"Failed to start machine: {response.text}")
            return False
        
        logger.info("Started machine with work order 1")
        
        # Wait for some cycles to complete
        logger.info("Waiting for machine cycles...")
        time.sleep(30)
        
        # Get machine cycles
        response = requests.get(f"{pcs_url}/machines/1/cycles")
        if response.status_code != 200:
            logger.error(f"Failed to get machine cycles: {response.text}")
            return False
        
        cycles = response.json()
        logger.info(f"Machine completed {len(cycles)} cycles")
        
        # Stop machine
        response = requests.post(f"{pcs_url}/machines/1/stop")
        if response.status_code != 200:
            logger.error(f"Failed to stop machine: {response.text}")
            return False
        
        logger.info("Stopped machine")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing PCS functionality: {str(e)}")
        return False

def test_data_synchronization():
    """Test data synchronization between systems"""
    try:
        # Start data synchronization
        response = requests.post(f"{interface_url}/api/sync/start")
        if response.status_code != 200:
            logger.error(f"Failed to start data synchronization: {response.text}")
            return False
        
        logger.info("Started data synchronization")
        
        # Wait for synchronization to run
        logger.info("Waiting for synchronization cycles...")
        time.sleep(30)
        
        # Check if production plan was synchronized to MES
        response = requests.get(f"{mes_url}/work-orders")
        if response.status_code != 200:
            logger.error(f"Failed to get work orders from MES: {response.text}")
            return False
        
        work_orders = response.json()
        if not work_orders:
            logger.error("No work orders found in MES after synchronization")
            return False
        
        logger.info(f"Found {len(work_orders)} work orders in MES after synchronization")
        
        # Check if machine status was synchronized from PCS to MES
        response = requests.get(f"{mes_url}/machines/1")
        if response.status_code != 200:
            logger.error(f"Failed to get machine from MES: {response.text}")
            return False
        
        machine = response.json()
        logger.info(f"Machine status in MES: {machine['status']}")
        
        # Check if production counts were synchronized from PCS to MES to ERP
        response = requests.get(f"{erp_url}/production-plans")
        if response.status_code != 200:
            logger.error(f"Failed to get production plans from ERP: {response.text}")
            return False
        
        plans = response.json()
        if not plans:
            logger.error("No production plans found in ERP")
            return False
        
        plan = plans[0]
        logger.info(f"Production plan in ERP: {plan['completed_quantity']}/{plan['quantity']}")
        
        # Stop data synchronization
        response = requests.post(f"{interface_url}/api/sync/stop")
        if response.status_code != 200:
            logger.error(f"Failed to stop data synchronization: {response.text}")
            return False
        
        logger.info("Stopped data synchronization")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing data synchronization: {str(e)}")
        return False

def test_interface_dashboard():
    """Test interface dashboard"""
    try:
        # Get dashboard summary
        response = requests.get(f"{interface_url}/api/dashboard/summary")
        if response.status_code != 200:
            logger.error(f"Failed to get dashboard summary: {response.text}")
            return False
        
        summary = response.json()
        logger.info(f"Dashboard summary: {json.dumps(summary, indent=2)}")
        
        # Get production data
        response = requests.get(f"{interface_url}/api/dashboard/production")
        if response.status_code != 200:
            logger.error(f"Failed to get production data: {response.text}")
            return False
        
        production = response.json()
        logger.info(f"Production data: {json.dumps(production, indent=2)}")
        
        # Get inventory data
        response = requests.get(f"{interface_url}/api/dashboard/inventory")
        if response.status_code != 200:
            logger.error(f"Failed to get inventory data: {response.text}")
            return False
        
        inventory = response.json()
        logger.info(f"Inventory data: {json.dumps(inventory, indent=2)}")
        
        # Get quality data
        response = requests.get(f"{interface_url}/api/dashboard/quality")
        if response.status_code != 200:
            logger.error(f"Failed to get quality data: {response.text}")
            return False
        
        quality = response.json()
        logger.info(f"Quality data: {json.dumps(quality, indent=2)}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing interface dashboard: {str(e)}")
        return False

def test_end_to_end_workflow():
    """Test end-to-end workflow from ERP to MES to PCS and back"""
    try:
        # Create material, product, BOM in ERP
        material_data = {
            'name': 'E2E Test Plastic',
            'description': 'End-to-end test material',
            'unit': 'kg',
            'quantity': 1000,
            'min_quantity': 100,
            'cost': 7.5
        }
        
        response = requests.post(f"{erp_url}/materials", json=material_data)
        if response.status_code != 201:
            logger.error(f"Failed to create material: {response.text}")
            return False
        
        material = response.json()
        material_id = material['id']
        
        product_data = {
            'name': 'E2E Test Product',
            'description': 'End-to-end test product',
            'unit': 'pcs'
        }
        
        response = requests.post(f"{erp_url}/products", json=product_data)
        if response.status_code != 201:
            logger.error(f"Failed to create product: {response.text}")
            return False
        
        product = response.json()
        product_id = product['id']
        
        bom_data = {
            'product_id': product_id,
            'materials': [
                {
                    'material_id': material_id,
                    'quantity': 0.25
                }
            ]
        }
        
        response = requests.post(f"{erp_url}/boms", json=bom_data)
        if response.status_code != 201:
            logger.error(f"Failed to create BOM: {response.text}")
            return False
        
        # Create production plan in ERP
        plan_data = {
            'product_id': product_id,
            'quantity': 50,
            'due_date': (time.time() + 86400) * 1000,  # Tomorrow
            'priority': 1,
            'status': 'pending'
        }
        
        response = requests.post(f"{erp_url}/production-plans", json=plan_data)
        if response.status_code != 201:
            logger.error(f"Failed to create production plan: {response.text}")
            return False
        
        plan = response.json()
        plan_id = plan['id']
        
        # Start data synchronization
        response = requests.post(f"{interface_url}/api/sync/start")
        if response.status_code != 200:
            logger.error(f"Failed to start data synchronization: {response.text}")
            return False
        
        # Wait for synchronization to create work orders
        logger.info("Waiting for synchronization to create work orders...")
        time.sleep(15)
        
        # Get work orders from MES
        response = requests.get(f"{mes_url}/work-orders")
        if response.status_code != 200:
            logger.error(f"Failed to get work orders from MES: {response.text}")
            return False
        
        work_orders = response.json()
        if not work_orders:
            logger.error("No work orders found in MES after synchronization")
            return False
        
        # Find work order for our production plan
        work_order = None
        for wo in work_orders:
            if wo.get('production_plan_id') == plan_id:
                work_order = wo
                break
        
        if not work_order:
            logger.error(f"No work order found for production plan {plan_id}")
            return False
        
        work_order_id = work_order['id']
        
        # Schedule work order on machine
        schedule_data = {
            'machine_id': 1,
            'work_order_id': work_order_id,
            'start_time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'end_time': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() + 3600)),
            'status': 'scheduled'
        }
        
        response = requests.post(f"{mes_url}/schedule", json=schedule_data)
        if response.status_code != 201:
            logger.error(f"Failed to schedule work order: {response.text}")
            return False
        
        # Wait for synchronization to start machine
        logger.info("Waiting for synchronization to start machine...")
        time.sleep(15)
        
        # Check if machine is running
        response = requests.get(f"{pcs_url}/machines/1/status")
        if response.status_code != 200:
            logger.error(f"Failed to get machine status: {response.text}")
            return False
        
        status = response.json()
        if not status.get('running', False):
            logger.warning("Machine not automatically started, starting manually")
            
            # Start machine manually
            response = requests.post(f"{pcs_url}/machines/1/start", json={'work_order_id': work_order_id})
            if response.status_code != 200:
                logger.error(f"Failed to start machine: {response.text}")
                return False
        
        # Wait for some cycles to complete
        logger.info("Waiting for machine cycles...")
        time.sleep(30)
        
        # Check if cycles were recorded
        response = requests.get(f"{pcs_url}/machines/1/cycles")
        if response.status_code != 200:
            logger.error(f"Failed to get machine cycles: {response.text}")
            return False
        
        cycles = response.json()
        logger.info(f"Machine completed {len(cycles)} cycles")
        
        # Wait for synchronization to update production counts
        logger.info("Waiting for synchronization to update production counts...")
        time.sleep(15)
        
        # Check if production counts were updated in MES
        response = requests.get(f"{mes_url}/work-orders/{work_order_id}/production-summary")
        if response.status_code != 200:
            logger.error(f"Failed to get production summary: {response.text}")
            return False
        
        summary = response.json()
        logger.info(f"Production summary in MES: {summary}")
        
        # Wait for synchronization to update ERP
        logger.info("Waiting for synchronization to update ERP...")
        time.sleep(15)
        
        # Check if production plan was updated in ERP
        response = requests.get(f"{erp_url}/production-plans/{plan_id}")
        if response.status_code != 200:
            logger.error(f"Failed to get production plan: {response.text}")
            return False
        
        plan = response.json()
        logger.info(f"Production plan in ERP: {plan['completed_quantity']}/{plan['quantity']}")
        
        # Stop machine
        response = requests.post(f"{pcs_url}/machines/1/stop")
        if response.status_code != 200:
            logger.error(f"Failed to stop machine: {response.text}")
            return False
        
        # Stop data synchronization
        response = requests.post(f"{interface_url}/api/sync/stop")
        if response.status_code != 200:
            logger.error(f"Failed to stop data synchronization: {response.text}")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error testing end-to-end workflow: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    logger.info("Starting integration tests...")
    
    # Start system
    processes = start_system()
    
    try:
        # Run tests
        run_test("System Availability", test_system_availability)
        run_test("ERP Functionality", test_erp_functionality)
        run_test("MES Functionality", test_mes_functionality)
        run_test("PCS Functionality", test_pcs_functionality)
        run_test("Data Synchronization", test_data_synchronization)
        run_test("Interface Dashboard", test_interface_dashboard)
        run_test("End-to-End Workflow", test_end_to_end_workflow)
        
        # Print test results
        logger.info(f"Test Results: {test_results['passed']}/{test_results['total']} tests passed")
        
        # Save test results to file
        with open(os.path.join(project_root, 'test_results.json'), 'w') as f:
            json.dump(test_results, f, indent=2)
        
        return test_results['failed'] == 0
    
    finally:
        # Stop system
        stop_system(processes)

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

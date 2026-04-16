"""
Data Synchronization Module
Provides mechanisms for synchronizing data between ERP, MES, and PCS systems
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
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'sync.log'))
    ]
)

logger = logging.getLogger('data_sync')

class DataSynchronizer:
    """Synchronizes data between ERP, MES, and PCS systems"""
    
    def __init__(self, config):
        """Initialize the data synchronizer"""
        self.config = config
        self.erp_url = f"http://{config['erp']['host']}:{config['erp']['port']}/api/{config['erp']['api_version']}"
        self.mes_url = f"http://{config['mes']['host']}:{config['mes']['port']}/api/{config['mes']['api_version']}"
        self.pcs_url = f"http://{config['pcs']['host']}:{config['pcs']['port']}/api/{config['pcs']['api_version']}"
        
        # Synchronization intervals (in seconds)
        self.sync_intervals = config['sync']['intervals']
        
        # Synchronization threads
        self.threads = {}
        self.stop_event = threading.Event()
        
        # Last sync timestamps
        self.last_sync = {
            'erp_to_mes': datetime.datetime.min,
            'mes_to_erp': datetime.datetime.min,
            'mes_to_pcs': datetime.datetime.min,
            'pcs_to_mes': datetime.datetime.min
        }
    
    def start(self):
        """Start all synchronization threads"""
        logger.info("Starting data synchronization...")
        
        # Clear stop event
        self.stop_event.clear()
        
        # Start ERP to MES sync thread
        self.threads['erp_to_mes'] = threading.Thread(
            target=self._sync_loop,
            args=('erp_to_mes', self._sync_erp_to_mes, self.sync_intervals['erp_to_mes'])
        )
        self.threads['erp_to_mes'].daemon = True
        self.threads['erp_to_mes'].start()
        
        # Start MES to ERP sync thread
        self.threads['mes_to_erp'] = threading.Thread(
            target=self._sync_loop,
            args=('mes_to_erp', self._sync_mes_to_erp, self.sync_intervals['mes_to_erp'])
        )
        self.threads['mes_to_erp'].daemon = True
        self.threads['mes_to_erp'].start()
        
        # Start MES to PCS sync thread
        self.threads['mes_to_pcs'] = threading.Thread(
            target=self._sync_loop,
            args=('mes_to_pcs', self._sync_mes_to_pcs, self.sync_intervals['mes_to_pcs'])
        )
        self.threads['mes_to_pcs'].daemon = True
        self.threads['mes_to_pcs'].start()
        
        # Start PCS to MES sync thread
        self.threads['pcs_to_mes'] = threading.Thread(
            target=self._sync_loop,
            args=('pcs_to_mes', self._sync_pcs_to_mes, self.sync_intervals['pcs_to_mes'])
        )
        self.threads['pcs_to_mes'].daemon = True
        self.threads['pcs_to_mes'].start()
        
        logger.info("All synchronization threads started")
    
    def stop(self):
        """Stop all synchronization threads"""
        logger.info("Stopping data synchronization...")
        
        # Set stop event
        self.stop_event.set()
        
        # Wait for threads to finish
        for name, thread in self.threads.items():
            thread.join(timeout=5)
            logger.info(f"Synchronization thread {name} stopped")
        
        # Clear threads
        self.threads = {}
        
        logger.info("All synchronization threads stopped")
    
    def _sync_loop(self, name, sync_func, interval):
        """Run a synchronization function in a loop.

        L2 fix: adds per-thread startup jitter (up to 20 % of interval) so
        that all sync threads do not fire simultaneously on startup, which
        previously flooded the logs and caused spurious connection errors.
        Also uses exponential back-off (capped at 60 s) on repeated failures
        instead of a fixed 5 s retry delay.
        """
        import random
        # Stagger thread starts to avoid thundering-herd on startup
        startup_jitter = random.uniform(0, max(1.0, interval * 0.2))
        logger.info(
            f"Starting {name} synchronization loop "
            f"(interval={interval}s, startup_jitter={startup_jitter:.1f}s)"
        )
        self.stop_event.wait(startup_jitter)

        consecutive_failures = 0
        while not self.stop_event.is_set():
            try:
                # Run synchronization function
                sync_func()

                # Update last sync timestamp
                self.last_sync[name] = datetime.datetime.now()
                consecutive_failures = 0  # reset back-off counter on success

                # Sleep until next sync, checking stop_event every 100 ms
                for _ in range(int(interval * 10)):
                    if self.stop_event.is_set():
                        break
                    time.sleep(0.1)

            except Exception as e:
                consecutive_failures += 1
                # Exponential back-off: 5s, 10s, 20s, 40s, capped at 60s
                backoff = min(60, 5 * (2 ** (consecutive_failures - 1)))
                logger.error(
                    f"Error in {name} synchronization (attempt {consecutive_failures}): "
                    f"{e}  — retrying in {backoff}s"
                )
                self.stop_event.wait(backoff)
    
    def _sync_erp_to_mes(self):
        """Synchronize data from ERP to MES"""
        logger.info("Synchronizing data from ERP to MES...")
        
        try:
            # Sync production plans
            self._sync_production_plans()
            
            # Sync materials
            self._sync_materials()
            
            logger.info("ERP to MES synchronization completed")
        
        except Exception as e:
            logger.error(f"Error synchronizing ERP to MES: {str(e)}")
            raise
    
    def _sync_mes_to_erp(self):
        """Synchronize data from MES to ERP"""
        logger.info("Synchronizing data from MES to ERP...")
        
        try:
            # Sync production counts
            self._sync_production_counts()
            
            # Sync material consumption
            self._sync_material_consumption()
            self._sync_material_transactions()  
            self._sync_produced_inventory()
            self._sync_production_plan_updates()
            logger.info("MES to ERP synchronization completed")
        
        except Exception as e:
            logger.error(f"Error synchronizing MES to ERP: {str(e)}")
            raise
    
    def _sync_mes_to_pcs(self):
        """Synchronize data from MES to PCS"""
        logger.info("Synchronizing data from MES to PCS...")
        
        try:
            # Sync work orders to machines

            self._sync_machines_to_pcs()  # ⬅️ Add this line
            self._sync_work_orders_to_machines()
            logger.info("MES to PCS synchronization completed")


        
        except Exception as e:
            logger.error(f"Error synchronizing MES to PCS: {str(e)}")
            raise
    
    def _sync_pcs_to_mes(self):
        """Synchronize data from PCS to MES"""
        logger.info("Synchronizing data from PCS to MES...")
        
        try:
            # Sync machine status
            self._sync_machine_status()
            
            # Sync production cycles
            self._sync_production_cycles()
            
            # Sync quality data
            self._sync_quality_data()
            
            logger.info("PCS to MES synchronization completed")
        
        except Exception as e:
            logger.error(f"Error synchronizing PCS to MES: {str(e)}")
            raise
    
    def _sync_production_plans(self):
        """Synchronize production plans from ERP to MES"""
        try:
            response = requests.get(f"{self.erp_url}/production-plans")
            if response.status_code != 200:
                logger.error(f"Failed to get production plans from ERP: {response.text}")
                return
            
            production_plans = response.json()
            if not production_plans:
                logger.info("🛠️ No production plans found in ERP to sync.")
                return
            
            logger.info(f"📦 Found {len(production_plans)} production plans to sync.")

            for plan in production_plans:
                if not plan.get('id'):
                    logger.warning(f"⚠️ Skipping plan without ID: {plan}")
                    continue

                # Skip pharma-managed plans – the pharma Streamlit app controls their
                # work order lifecycle directly via its own integration layer.
                # Pharma plans are identified by the 'PP-ORD-' or 'PP-BAT-' prefixes
                # set by pharma/app/integration/erp_client.py.
                plan_number = plan.get('plan_number', '')
                if plan_number.startswith('PP-ORD-') or plan_number.startswith('PP-BAT-'):
                    logger.info(f"⏭️ Skipping pharma-managed plan {plan_number} (id={plan['id']})")
                    continue

                logger.info(f"🔄 Syncing production plan {plan['id']}...")

                # 1. Check if plan exists in MES
                response = requests.get(f"{self.mes_url}/production-plans/{plan['id']}")
                
                if response.status_code == 404:
                    logger.info(f"Production plan {plan['id']} not found in MES, creating it...")
                    create_response = requests.post(f"{self.mes_url}/production-plans", json=plan)
                    if create_response.status_code != 201:
                        logger.error(f"❌ Failed to create production plan {plan['id']} in MES: {create_response.text}")
                        continue
                    logger.info(f"✅ Created production plan {plan['id']} in MES.")
                elif response.status_code != 200:
                    logger.error(f"❌ Failed checking production plan {plan['id']} in MES: {response.text}")
                    continue

                # 2. Check if work orders exist
                work_orders_response = requests.get(f"{self.mes_url}/production-plans/{plan['id']}/work-orders")
                if work_orders_response.status_code == 404:
                    logger.info(f"No work orders found for production plan {plan['id']}.")
                    existing_work_orders = []
                elif work_orders_response.status_code == 200:
                    existing_work_orders = work_orders_response.json()
                else:
                    logger.error(f"❌ Failed checking work orders for plan {plan['id']}: {work_orders_response.text}")
                    continue

                # 3. Create work orders if needed
                if not existing_work_orders:
                    logger.info(f"🛠️ Generating work orders for production plan {plan['id']}...")
                    create_work_orders_response = requests.post(f"{self.mes_url}/production-plans/{plan['id']}/generate-work-orders")
                    if create_work_orders_response.status_code != 201:
                        logger.error(f"❌ Failed to create work orders for plan {plan['id']}: {create_work_orders_response.text}")
                    else:
                        logger.info(f"✅ Created work orders for production plan {plan['id']}.")

            logger.info(f"✅ Synchronized {len(production_plans)} production plans from ERP to MES.")

        except Exception as e:
            logger.error(f"❌ Error synchronizing production plans: {str(e)}")

                    
    def _sync_materials(self):
        """Synchronize materials from ERP to MES"""
        try:
            response = requests.get(f"{self.erp_url}/materials")
            if response.status_code != 200:
                logger.error(f"Failed to get materials from ERP: {response.text}")
                return

            materials = response.json()

            for material in materials:
                # Try to get material by code (MES matches by code)
                response = requests.get(f"{self.mes_url}/materials/code/{material['code']}")
                
                if response.status_code == 404:
                    # Not found, create new
                    response = requests.post(f"{self.mes_url}/materials", json=material)
                    if response.status_code != 201:
                        logger.error(f"Failed to create material {material['code']} in MES: {response.text}")
                        continue
                    logger.info(f"Created material {material['code']} in MES")
                
                elif response.status_code == 200:
                    # Exists, update it
                    mes_material = response.json()
                    material_id = mes_material['id']
                    response = requests.put(f"{self.mes_url}/materials/{material_id}", json=material)
                    if response.status_code != 200:
                        logger.error(f"Failed to update material {material['code']} in MES: {response.text}")
                        continue
                    logger.info(f"Updated material {material['code']} in MES")
                
                else:
                    logger.error(f"Failed to check material {material['code']} in MES: {response.text}")

            logger.info(f"Synchronized {len(materials)} materials from ERP to MES")

        except Exception as e:
            logger.error(f"Error synchronizing materials: {str(e)}")
            raise

    
    def _sync_production_counts(self):
        """Synchronize production counts from MES to ERP"""
        try:
            # Get active work orders from MES
            response = requests.get(f"{self.mes_url}/work-orders/active")
            if response.status_code != 200:
                logger.error(f"Failed to get active work orders from MES: {response.text}")
                return
            
            work_orders = response.json()
            
            # For each work order, get production counts and update ERP
            for work_order in work_orders:
                # Get production summary for work order
                response = requests.get(f"{self.mes_url}/work-orders/{work_order['id']}/production-summary")
                if response.status_code != 200:
                    logger.error(f"Failed to get production summary for work order {work_order['id']}: {response.text}")
                    continue
                
                production_summary = response.json()
                
                # Debug the full summary before using it
                logger.debug(f"Production summary for work order {work_order['id']}: {production_summary}")

                # Update production counts in ERP using correct keys
                update_response = requests.put(
                    f"{self.erp_url}/production-plans/{work_order['production_plan_id']}/update-counts",
                    json={
                        'work_order_id': work_order['id'],
                        'good_count': production_summary['total_good'],
                        'reject_count': production_summary['total_reject'],
                        'rework_count': production_summary['total_rework']
                    }
                )

                
                if update_response.status_code != 200:
                    logger.error(f"Failed to update production counts for work order {work_order['id']} in ERP: {response.text}")
                    continue
                
                logger.info(f"Updated production counts for work order {work_order['id']} in ERP")
            
            logger.info(f"Synchronized production counts for {len(work_orders)} work orders from MES to ERP")
        
        except Exception as e:
            logger.error(f"Error synchronizing production counts: {str(e)}")
            raise
        
   
    def _sync_produced_inventory(self):
        """Synchronize produced inventory from MES to ERP"""
        logger.info("Synchronizing produced inventory from MES to ERP...")

        try:
            response = requests.get(f"{self.mes_url}/work-orders/completed")
            if response.status_code != 200:
                logger.error(f"Failed to fetch completed work orders: {response.text}")
                return
            
            completed_work_orders = response.json()

            if not completed_work_orders:
                logger.info("🛠️ No completed work orders to sync for produced inventory.")
                return

            for work_order in completed_work_orders:
                # Push finished goods etc...
                logger.info(f"📦 Syncing inventory for completed work order {work_order['id']}")
                # (Put your inventory sync logic here)

            logger.info(f"✅ Produced inventory synchronization completed.")

        except Exception as e:
            logger.error(f"Error during produced inventory sync: {str(e)}")


    def _sync_material_consumption(self):
        """Synchronize material consumption from MES to ERP"""
        try:
            # Get active work orders from MES
            response = requests.get(f"{self.mes_url}/work-orders/active")
            if response.status_code != 200:
                logger.error(f"Failed to get active work orders from MES: {response.text}")
                return
            
            work_orders = response.json()
            
            # For each work order, get material transactions and update ERP
            for work_order in work_orders:
                # Get material transactions for work order
                response = requests.get(f"{self.mes_url}/work-orders/{work_order['id']}/material-transactions")
                if response.status_code != 200:
                    logger.error(f"Failed to get material transactions for work order {work_order['id']}: {response.text}")
                    continue
                
                transactions = response.json()
                
                # Filter consumption transactions
                consumption_transactions = [t for t in transactions if t['transaction_type'] == 'consumption']
                
                # Skip if no consumption transactions
                if not consumption_transactions:
                    continue
                
                # Update material consumption in ERP
                for transaction in consumption_transactions:
                    # Check if transaction already synced (based on transaction ID)
                    response = requests.get(f"{self.erp_url}/material-transactions/mes/{transaction['id']}")
                    
                    if response.status_code == 404:
                        # Transaction not synced, create it
                        response = requests.post(
                            f"{self.erp_url}/material-transactions",
                            json={
                                'material_id': transaction['material_id'],
                                'quantity': transaction['quantity'],
                                'transaction_type': 'consumption',
                                'reference_id': transaction['id'],
                                'reference_type': 'mes_transaction',
                                'work_order_id': work_order['id']
                            }
                        )
                        
                        if response.status_code != 201:
                            logger.error(f"Failed to create material transaction in ERP: {response.text}")
                            continue
                        
                        logger.info(f"Created material consumption transaction in ERP for MES transaction {transaction['id']}")
                
                logger.info(f"Synchronized {len(consumption_transactions)} material consumption transactions for work order {work_order['id']}")
            
            logger.info(f"Synchronized material consumption for {len(work_orders)} work orders from MES to ERP")
        
        except Exception as e:
            logger.error(f"Error synchronizing material consumption: {str(e)}")
            raise

    def _sync_material_transactions(self):
        """Synchronize material transactions from MES to ERP"""
        logger.info("Synchronizing material transactions from MES to ERP...")

        try:
            # Get completed work orders from MES
            response = requests.get(f"{self.mes_url}/work-orders/completed")
            if response.status_code != 200:
                logger.error(f"Failed to fetch completed work orders: {response.text}")
                return
            
            completed_work_orders = response.json()

            if not completed_work_orders:
                logger.info("🛠️ No completed work orders to sync for material transactions.")
                return
            
            # Now loop safely
            for work_order in completed_work_orders:
                work_order_id = work_order['id']

                # Get material transactions for this work order
                response = requests.get(f"{self.mes_url}/work-orders/{work_order_id}/material-transactions")
                if response.status_code != 200:
                    logger.error(f"Failed to get material transactions for work order {work_order_id}: {response.text}")
                    continue

                transactions = response.json()

                if not transactions:
                    logger.info(f"🛠️ No material transactions for work order {work_order_id}.")
                    continue

                for transaction in transactions:
                    # Push transaction to ERP
                    response = requests.post(f"{self.erp_url}/material-transactions", json=transaction)
                    if response.status_code != 201:
                        logger.error(f"Failed to push transaction for work order {work_order_id}: {response.text}")
                    else:
                        logger.info(f"Pushed material transaction for work order {work_order_id} to ERP.")
            
            logger.info(f"✅ Material transactions synchronization completed.")

        except Exception as e:
            logger.error(f"Error during material transaction sync: {str(e)}")


    def _sync_work_orders_to_machines(self):
        """Synchronize work orders from MES to PCS machines"""
        try:
            # Get scheduled work orders from MES
            response = requests.get(f"{self.mes_url}/schedule")
            if response.status_code != 200:
                logger.error(f"Failed to get schedule from MES: {response.text}")
                return
            
            schedule_entries = response.json()
            
            # Get current time
            now = datetime.datetime.now()
            
            # Filter entries that should be running now
            current_entries = [
                entry for entry in schedule_entries 
                if (entry['scheduled_start'] <= now.isoformat() and 
                    (entry['scheduled_end'] is None or entry['scheduled_end'] >= now.isoformat()))
            ]
            
            logger.debug(f"Current entries for synchronization: {current_entries}")
            
            for entry in current_entries:
                machine_id = entry['machine_id']
                work_order_id = entry['work_order_id']
                
                # Check machine status in PCS
                response = requests.get(f"{self.pcs_url}/machines/{machine_id}/status")
                if response.status_code != 200:
                    logger.error(f"Failed to get status for machine {machine_id} from PCS: {response.text}")
                    continue
                
                machine_status = response.json()
                
                # Start machine if necessary
                if (not machine_status.get('running', False) or machine_status.get('work_order_id') != work_order_id):
                    response = requests.post(
                        f"{self.pcs_url}/machines/{machine_id}/start",
                        json={'work_order_id': work_order_id}
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to start machine {machine_id} with work order {work_order_id}: {response.text}")
                        continue
                    
                    logger.info(f"Started machine {machine_id} with work order {work_order_id}")
            
            # Handle ended entries (machines that should have stopped)
            ended_entries = [
                entry for entry in schedule_entries 
                if entry['scheduled_end'] is not None and entry['scheduled_end'] < now.isoformat()
            ]
            
            for entry in ended_entries:
                machine_id = entry['machine_id']
                work_order_id = entry['work_order_id']
                
                # Check if machine should be stopped
                response = requests.get(f"{self.pcs_url}/machines/{machine_id}/status")
                if response.status_code != 200:
                    logger.error(f"Failed to get status for machine {machine_id} from PCS: {response.text}")
                    continue
                
                machine_status = response.json()
                
                if machine_status.get('running', False) and machine_status.get('work_order_id') == work_order_id:
                    response = requests.post(f"{self.pcs_url}/machines/{machine_id}/stop")
                    
                    if response.status_code != 200:
                        logger.error(f"Failed to stop machine {machine_id}: {response.text}")
                        continue
                    
                    logger.info(f"Stopped machine {machine_id} after work order {work_order_id} completion")
            
            logger.info(f"Synchronized {len(current_entries)} current and {len(ended_entries)} ended work orders from MES to PCS")
        
        except Exception as e:
            logger.error(f"Error synchronizing work orders to machines: {str(e)}")
            raise
    def _sync_machines_to_pcs(self):
        """Synchronize machine definitions from MES to PCS"""
        try:
            logger.info("Synchronizing machine definitions from MES to PCS...")
            
            # 1. Get machines from MES
            response = requests.get(f"{self.mes_url}/machines")
            if response.status_code != 200:
                logger.error(f"Failed to fetch machines from MES: {response.text}")
                return

            mes_machines = response.json()

            # 2. Get current machines from PCS
            pcs_response = requests.get(f"{self.pcs_url}/machines/status")
            pcs_machines = pcs_response.json() if pcs_response.status_code == 200 else {}

            pcs_machine_ids = {int(mid) for mid in pcs_machines}

            for machine in mes_machines:
                machine_id = machine['id']
                if machine_id not in pcs_machine_ids:
                    logger.info(f"Registering machine {machine_id} in PCS")
                    reg_response = requests.post(
                        f"{self.pcs_url}/machines",
                        json={"machine_id": machine_id}
                    )
                    if reg_response.status_code != 201:
                        logger.error(f"Failed to register machine {machine_id} in PCS: {reg_response.text}")
                    else:
                        logger.info(f"Registered machine {machine_id} in PCS")

            logger.info(f"Synchronized {len(mes_machines)} machines from MES to PCS")

        except Exception as e:
            logger.error(f"Error synchronizing machines to PCS: {str(e)}")

    
    
    
    
    def _sync_machine_status(self):
        """Synchronize machine status from PCS to MES"""
        try:
            # Get all machines status from PCS
            response = requests.get(f"{self.pcs_url}/machines/status")
            if response.status_code != 200:
                logger.error(f"Failed to get machines status from PCS: {response.text}")
                return
            logger.debug(f"[PCS->MES] Received machine status payload: {response.text}")

            machines_status = response.json()
            
            # For each machine, update status in MES
            for machine_id, status in machines_status.items():
                # Update machine status in MES
                logger.debug(f"Syncing status for machine {machine_id}: {status}")
                response = requests.put(
                    f"{self.mes_url}/machines/{machine_id}/status",
                    json={'status': status['state']}
                )
                
                logger.debug(f"Response status: {response.status_code}, Response text: {response.text}")
                if response.status_code != 200:
                    logger.error(f"Failed to update status for machine {machine_id} in MES: {response.text}")
                    continue
                logger.info(f"Updated status for machine {machine_id} in MES to {status['state']}")
            
            logger.info(f"Synchronized status for {len(machines_status)} machines from PCS to MES")
        
        except Exception as e:
            logger.error(f"Error synchronizing machine status: {str(e)}")
            raise
    
    def _sync_production_cycles(self):
        """Synchronize completed production cycles from PCS to MES."""
        logger.info("🔄 Synchronizing production cycles from PCS to MES...")

        try:
            # Step 1: Get all completed cycles from PCS
            response = requests.get(f"{self.pcs_url}/machines/cycles/completed")
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to get completed cycles from PCS: {response.text}")
                return

            completed_cycles = response.json()  # Expect a list of completed cycle records
            
            logger.info(f"🛠️ Found {len(completed_cycles)} completed cycles ready to sync.")

            for cycle in completed_cycles:
                machine_id = cycle['machine_id']
                work_order_id = cycle['work_order_id']
                cycle_number = cycle['cycle_number']
                cycle_time = cycle.get('cycle_time', 0)

                # Step 2: Send production count increment to MES
                logger.info(f"📤 Reporting cycle {cycle_number} for work order {work_order_id} (machine {machine_id}) to MES...")

                payload = {
                    'good': 1,      # Assume one good part per cycle
                    'reject': 0,
                    'rework': 0
                }

                mes_response = requests.post(
                    f"{self.mes_url}/work-orders/{work_order_id}/increment-count",
                    json=payload
                )

                if mes_response.status_code == 201:
                    logger.info(f"✅ MES production count incremented for work order {work_order_id}")
                    
                    # Step 3: Mark cycle as synced in PCS
                    mark_synced = requests.post(
                        f"{self.pcs_url}/machines/cycles/{cycle['id']}/mark-synced"
                    )
                    if mark_synced.status_code == 200:
                        logger.info(f"✅ Cycle {cycle['id']} marked as synced.")
                    else:
                        logger.warning(f"⚠️ Failed to mark cycle {cycle['id']} as synced: {mark_synced.text}")
                else:
                    logger.error(f"❌ Failed to increment production count in MES: {mes_response.text}")

        except Exception as e:
            logger.error(f"💥 Error during cycle synchronization: {str(e)}")

    def _sync_production_plan_updates(self):
        """Synchronize completed production quantities from MES to ERP"""
        logger.info("Synchronizing production plan updates from MES to ERP...")
        try:
            # Fetch all completed work orders
            response = requests.get(f"{self.mes_url}/work-orders/completed")
            if response.status_code != 200:
                logger.error(f"Failed to fetch completed work orders: {response.text}")
                return
            
            work_orders = response.json()

            for work_order in work_orders:
                plan_id = work_order.get("production_plan_id")
                good_quantity = work_order.get("quantity")
                work_order_id = work_order.get("id")

                if plan_id and good_quantity:
                    logger.info(f"Updating production plan {plan_id} with work order {work_order_id} completion")

                    payload = {
                        "work_order_id": work_order_id,
                        "good_count": good_quantity,
                        "reject_count": 0,  # You could adjust this if needed later
                        "rework_count": 0
                    }

                    response = requests.put(
                        f"{self.erp_url}/production-plans/{plan_id}/update-counts",
                        json=payload
                    )

                    if response.status_code == 200:
                        logger.info(f"✅ Updated production plan {plan_id} successfully")
                    else:
                        logger.error(f"❌ Failed to update production plan {plan_id}: {response.text}")

            logger.info("Finished production plan synchronization.")

        except Exception as e:
            logger.error(f"Error during production plan sync: {str(e)}")

    
    
    
    
    def _sync_quality_data(self):
        """Synchronize quality data from PCS to MES"""
        try:
            # Get all machines from PCS
            response = requests.get(f"{self.pcs_url}/machines/status")
            if response.status_code != 200:
                logger.error(f"Failed to get machines from PCS: {response.text}")
                return
            
            machines_status = response.json()
            
            # For each machine, get alarms and create quality checks in MES
            for machine_id, status in machines_status.items():
                # Skip machines that don't have a work order
                if not status.get('work_order_id'):
                    continue
                
                work_order_id = status['work_order_id']
                
                # Get alarms for this machine
                response = requests.get(f"{self.pcs_url}/machines/{machine_id}/alarms")
                if response.status_code != 200:
                    logger.error(f"Failed to get alarms for machine {machine_id} from PCS: {response.text}")
                    continue
                
                alarms = response.json()
                
                # Filter active alarms
                active_alarms = [a for a in alarms if a['status'] == 'active']
                
                # Fetch existing quality checks for this work order once per machine
                # to perform real deduplication (M3 fix: the MES GET /quality-checks
                # endpoint ignores query params, so we use the work-order-scoped
                # endpoint and match by alarm id embedded in the 'notes' field).
                existing_notes: set = set()
                wo_checks_resp = requests.get(
                    f"{self.mes_url}/work-orders/{work_order_id}/quality-checks"
                )
                if wo_checks_resp.status_code == 200:
                    for chk in wo_checks_resp.json():
                        if chk.get('notes'):
                            existing_notes.add(chk['notes'])
                else:
                    logger.warning(
                        f"Could not fetch existing quality checks for WO {work_order_id}: "
                        f"{wo_checks_resp.status_code}"
                    )

                # For each active alarm, create a quality check in MES if not already exists
                for alarm in active_alarms:
                    alarm_id = alarm['id']
                    # Build the canonical notes tag used for deduplication
                    notes_tag = f"[PCS Alarm id={alarm_id}]"

                    # Skip if a quality check with this alarm's notes tag already exists
                    if any(notes_tag in n for n in existing_notes):
                        logger.debug(
                            f"Quality check for alarm {alarm_id} already exists, skipping"
                        )
                        continue

                    # Map PCS alarm severity to MES quality check status.
                    # PCS severities: 'info', 'warning', 'error', 'critical', 'high'.
                    # MES QualityCheck.status accepts: 'pass', 'fail', 'warning'.
                    alarm_severity = alarm.get('severity', 'info')
                    if alarm_severity in ('error', 'critical', 'high'):
                        qc_status = 'fail'
                    elif alarm_severity == 'warning':
                        qc_status = 'warning'
                    else:
                        qc_status = 'pass'

                    notes_value = f"{notes_tag} {alarm.get('description', '')}".strip()

                    # Create quality check using only fields the MES model supports
                    response = requests.post(
                        f"{self.mes_url}/quality-checks",
                        json={
                            'work_order_id': work_order_id,
                            'parameter': alarm.get('alarm_code', 'ALARM'),
                            'value': 0.0,
                            'status': qc_status,
                            'notes': notes_value,
                        }
                    )

                    if response.status_code != 201:
                        logger.error(
                            f"Failed to create quality check for alarm {alarm_id}: {response.text}"
                        )
                        continue

                    # Track newly created note so subsequent alarms in the same
                    # loop iteration also benefit from deduplication
                    existing_notes.add(notes_value)
                    logger.info(
                        f"Created quality check for alarm {alarm_id} on machine {machine_id}"
                    )
            
            logger.info(f"Synchronized quality data for {len(machines_status)} machines from PCS to MES")
        
        except Exception as e:
            logger.error(f"Error synchronizing quality data: {str(e)}")
            raise
    
    def get_status(self):
        """Get synchronization status"""
        return {
            'running': bool(self.threads),
            'last_sync': {name: ts.isoformat() for name, ts in self.last_sync.items()},
            'sync_intervals': self.sync_intervals
        }


def load_config():
    """Load configuration from file"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def main():
    """Main entry point"""
    logger.info("Starting data synchronization service...")
    
    try:
        # Load configuration
        config = load_config()
        
        # Create synchronizer
        synchronizer = DataSynchronizer(config)
        
        # Start synchronization
        synchronizer.start()
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping...")
        finally:
            # Stop synchronization
            synchronizer.stop()
        
        logger.info("Data synchronization service stopped")
    
    except Exception as e:
        logger.error(f"Error in data synchronization service: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

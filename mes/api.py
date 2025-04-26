"""
MES Emulator - API Endpoints
Provides REST API endpoints for the MES emulator
"""
import os
import yaml
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from services import (


    WorkOrderService, MachineService, SchedulingService, QualityService,
    MaterialTrackingService, ProductionCountService, DowntimeService,MaterialService,MaterialByCodeAPI,ProductionPlanService
)

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# Create Flask app
app = Flask(__name__)

# CORS configuration
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

api = Api(app)

# API version prefix
api_version = config['mes']['api_version']
API_PREFIX = f"/api/{api_version}"

# ERP connection
erp_connection = config['mes']['erp_connection']
ERP_API_URL = erp_connection['url']

# Error handling
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404

@app.errorhandler(400)
def bad_request(error):
    return {'error': 'Bad request'}, 400

@app.errorhandler(500)
def server_error(error):
    return {'error': 'Internal server error'}, 500

@app.route('/api/v1/status')
def status():
    return {'status': 'ok', 'service': 'MES'}, 200


# Work Orders API
class WorkOrderListAPI(Resource):
    def get(self):
        """Get all work orders"""
        try:
            work_orders = WorkOrderService.get_all_work_orders()
            return work_orders
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new work order"""
        try:
            work_order_data = request.get_json()
            if not work_order_data:
                return {'error': 'No data provided'}, 400
            
            work_order = WorkOrderService.create_work_order(work_order_data)
            return work_order, 201
        except Exception as e:
            return {'error': str(e)}, 500

class WorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get work order by ID"""
        try:
            work_order = WorkOrderService.get_work_order_by_id(work_order_id)
            if not work_order:
                return {'error': 'Work order not found'}, 404
            
            return work_order
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, work_order_id):
        """Update a work order"""
        try:
            work_order_data = request.get_json()
            if not work_order_data:
                return {'error': 'No data provided'}, 400
            
            work_order = WorkOrderService.update_work_order(work_order_id, work_order_data)
            if not work_order:
                return {'error': 'Work order not found'}, 404
            
            return work_order
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, work_order_id):
        """Delete a work order"""
        try:
            result = WorkOrderService.delete_work_order(work_order_id)
            if not result:
                return {'error': 'Work order not found'}, 404
            
            return {'message': 'Work order deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class WorkOrderByNumberAPI(Resource):
    def get(self, work_order_number):
        """Get work order by work order number"""
        try:
            work_order = WorkOrderService.get_work_order_by_number(work_order_number)
            if not work_order:
                return {'error': 'Work order not found'}, 404
            
            return work_order
        except Exception as e:
            return {'error': str(e)}, 500

class WorkOrderStatusAPI(Resource):
    def put(self, work_order_id):
        """Update work order status"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return {'error': 'No status provided'}, 400
            
            work_order = WorkOrderService.update_work_order_status(work_order_id, data['status'])
            if not work_order:
                return {'error': 'Work order not found'}, 404
            
            return work_order
        except Exception as e:
            return {'error': str(e)}, 500

class WorkOrdersByMachineAPI(Resource):
    def get(self, machine_id):
        """Get work orders for a specific machine"""
        try:
            work_orders = WorkOrderService.get_work_orders_by_machine(machine_id)
            return work_orders
        except Exception as e:
            return {'error': str(e)}, 500

class ActiveWorkOrdersAPI(Resource):
    def get(self):
        """Get all active work orders"""
        try:
            work_orders = WorkOrderService.get_active_work_orders()
            return work_orders
        except Exception as e:
            return {'error': str(e)}, 500

class CompletedWorkOrdersAPI(Resource):
    def get(self):
        """Get all completed work orders"""
        try:
            work_orders = WorkOrderService.get_completed_work_orders()
            return work_orders
        except Exception as e:
            return {'error': str(e)}, 500
        
class WorkOrdersByProductionPlanAPI(Resource):
    def get(self, production_plan_id):
        work_orders = WorkOrderService.get_work_orders_by_plan(production_plan_id)
        return work_orders or [], 200


class GenerateWorkOrdersAPI(Resource):
    def post(self, production_plan_id):
        try:
            work_orders = WorkOrderService.create_work_order_from_production_plan(production_plan_id, ERP_API_URL)
            if not work_orders:
                return {'error': 'Failed to create work orders from production plan'}, 400
            return work_orders, 201
        except Exception as e:
            return {'error': str(e)}, 500


# Machines API
class MachineListAPI(Resource):
    def get(self):
        """Get all machines"""
        try:
            machines = MachineService.get_all_machines()
            return machines
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new machine"""
        try:
            machine_data = request.get_json()
            if not machine_data:
                return {'error': 'No data provided'}, 400
            
            machine = MachineService.create_machine(machine_data)
            return machine, 201
        except Exception as e:
            return {'error': str(e)}, 500

class MachineAPI(Resource):
    def get(self, machine_id):
        """Get machine by ID"""
        try:
            machine = MachineService.get_machine_by_id(machine_id)
            if not machine:
                return {'error': 'Machine not found'}, 404
            
            return machine
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, machine_id):
        """Update a machine"""
        try:
            machine_data = request.get_json()
            if not machine_data:
                return {'error': 'No data provided'}, 400
            
            machine = MachineService.update_machine(machine_id, machine_data)
            if not machine:
                return {'error': 'Machine not found'}, 404
            
            return machine
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, machine_id):
        """Delete a machine"""
        try:
            result = MachineService.delete_machine(machine_id)
            if not result:
                return {'error': 'Machine not found'}, 404
            
            return {'message': 'Machine deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialAPI(Resource):
    def put(self, material_id):
        data = request.get_json()
        updated = MaterialService.update_material(material_id, data)
        if not updated:
            return {'error': 'Not found'}, 404
        return updated




class MachineByCodeAPI(Resource):
    def get(self, machine_code):
        """Get machine by machine code"""
        try:
            machine = MachineService.get_machine_by_code(machine_code)
            if not machine:
                return {'error': 'Machine not found'}, 404
            
            return machine
        except Exception as e:
            return {'error': str(e)}, 500

class MachineStatusAPI(Resource):
    def put(self, machine_id):
        """Update machine status"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return {'error': 'No status provided'}, 400
            
            machine = MachineService.update_machine_status(machine_id, data['status'])
            if not machine:
                return {'error': 'Machine not found'}, 404
            
            return machine
        except Exception as e:
            return {'error': str(e)}, 500

class AvailableMachinesAPI(Resource):
    def get(self):
        """Get all available machines"""
        try:
            machines = MachineService.get_available_machines()
            return machines
        except Exception as e:
            return {'error': str(e)}, 500

class MachinesByTypeAPI(Resource):
    def get(self, machine_type):
        """Get machines by type"""
        try:
            machines = MachineService.get_machines_by_type(machine_type)
            return machines
        except Exception as e:
            return {'error': str(e)}, 500

# Production Schedule API
class ScheduleListAPI(Resource):
    def get(self):
        """Get all schedule entries"""
        try:
            entries = SchedulingService.get_all_schedule_entries()
            return entries
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new schedule entry"""
        try:
            schedule_data = request.get_json()
            if not schedule_data:
                return {'error': 'No data provided'}, 400
            
            entry = SchedulingService.create_schedule_entry(schedule_data)
            if not entry:
                return {'error': 'Failed to create schedule entry'}, 400
            
            return entry, 201
        except Exception as e:
            return {'error': str(e)}, 500

class ScheduleEntryAPI(Resource):
    def get(self, entry_id):
        """Get schedule entry by ID"""
        try:
            entry = SchedulingService.get_schedule_entry_by_id(entry_id)
            if not entry:
                return {'error': 'Schedule entry not found'}, 404
            
            return entry
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, entry_id):
        """Update a schedule entry"""
        try:
            schedule_data = request.get_json()
            if not schedule_data:
                return {'error': 'No data provided'}, 400
            
            entry = SchedulingService.update_schedule_entry(entry_id, schedule_data)
            if not entry:
                return {'error': 'Schedule entry not found'}, 404
            
            return entry
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, entry_id):
        """Delete a schedule entry"""
        try:
            result = SchedulingService.delete_schedule_entry(entry_id)
            if not result:
                return {'error': 'Schedule entry not found'}, 404
            
            return {'message': 'Schedule entry deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class MachineScheduleAPI(Resource):
    def get(self, machine_id):
        """Get schedule for a specific machine"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            entries = SchedulingService.get_machine_schedule(machine_id, start_date, end_date)
            return entries
        except Exception as e:
            return {'error': str(e)}, 500

class WorkOrderScheduleAPI(Resource):
    def get(self, work_order_id):
        """Get schedule entries for a specific work order"""
        try:
            entries = SchedulingService.get_work_order_schedule(work_order_id)
            return entries
        except Exception as e:
            return {'error': str(e)}, 500

class MachineAvailabilityAPI(Resource):
    def get(self, machine_id):
        """Check if a machine is available during the specified time period"""
        try:
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            
            if not start_time or not end_time:
                return {'error': 'Start time and end time are required'}, 400
            
            availability = SchedulingService.check_machine_availability(machine_id, start_time, end_time)
            return availability
        except Exception as e:
            return {'error': str(e)}, 500

class AutoScheduleWorkOrderAPI(Resource):
    def post(self, work_order_id):
        """Automatically schedule a work order on an available machine"""
        try:
            data = request.get_json() or {}
            estimated_duration_hours = data.get('estimated_duration_hours')
            
            result = SchedulingService.auto_schedule_work_order(work_order_id, estimated_duration_hours)
            if not result:
                return {'error': 'Failed to schedule work order'}, 400
            
            return result
        except Exception as e:
            return {'error': str(e)}, 500

# Quality Control API
class QualityCheckListAPI(Resource):
    def get(self):
        """Get all quality checks"""
        try:
            checks = QualityService.get_all_quality_checks()
            return checks
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new quality check"""
        try:
            check_data = request.get_json()
            if not check_data:
                return {'error': 'No data provided'}, 400
            
            check = QualityService.create_quality_check(check_data)
            return check, 201
        except Exception as e:
            return {'error': str(e)}, 500

class QualityCheckAPI(Resource):
    def get(self, check_id):
        """Get quality check by ID"""
        try:
            check = QualityService.get_quality_check_by_id(check_id)
            if not check:
                return {'error': 'Quality check not found'}, 404
            
            return check
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, check_id):
        """Update a quality check"""
        try:
            check_data = request.get_json()
            if not check_data:
                return {'error': 'No data provided'}, 400
            
            check = QualityService.update_quality_check(check_id, check_data)
            if not check:
                return {'error': 'Quality check not found'}, 404
            
            return check
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, check_id):
        """Delete a quality check"""
        try:
            result = QualityService.delete_quality_check(check_id)
            if not result:
                return {'error': 'Quality check not found'}, 404
            
            return {'message': 'Quality check deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class QualityChecksByWorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get quality checks for a specific work order"""
        try:
            checks = QualityService.get_quality_checks_by_work_order(work_order_id)
            return checks
        except Exception as e:
            return {'error': str(e)}, 500

class QualitySummaryByWorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get quality summary for a specific work order"""
        try:
            summary = QualityService.get_quality_summary_by_work_order(work_order_id)
            return summary
        except Exception as e:
            return {'error': str(e)}, 500

# Material Tracking API
class MaterialTransactionListAPI(Resource):
    def get(self):
        """Get all material transactions"""
        try:
            transactions = MaterialTrackingService.get_all_material_transactions()
            return transactions
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new material transaction"""
        try:
            transaction_data = request.get_json()
            if not transaction_data:
                return {'error': 'No data provided'}, 400
            
            transaction = MaterialTrackingService.create_material_transaction(transaction_data)
            return transaction, 201
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialTransactionAPI(Resource):
    def get(self, transaction_id):
        """Get material transaction by ID"""
        try:
            transaction = MaterialTrackingService.get_material_transaction_by_id(transaction_id)
            if not transaction:
                return {'error': 'Material transaction not found'}, 404
            
            return transaction
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, transaction_id):
        """Update a material transaction"""
        try:
            transaction_data = request.get_json()
            if not transaction_data:
                return {'error': 'No data provided'}, 400
            
            transaction = MaterialTrackingService.update_material_transaction(transaction_id, transaction_data)
            if not transaction:
                return {'error': 'Material transaction not found'}, 404
            
            return transaction
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, transaction_id):
        """Delete a material transaction"""
        try:
            result = MaterialTrackingService.delete_material_transaction(transaction_id)
            if not result:
                return {'error': 'Material transaction not found'}, 404
            
            return {'message': 'Material transaction deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialTransactionsByWorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get material transactions for a specific work order"""
        try:
            transactions = MaterialTrackingService.get_material_transactions_by_work_order(work_order_id)
            return transactions
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialTransactionsByMaterialAPI(Resource):
    def get(self, material_id):
        """Get material transactions for a specific material"""
        try:
            transactions = MaterialTrackingService.get_material_transactions_by_material(material_id)
            return transactions
        except Exception as e:
            return {'error': str(e)}, 500

class AllocateMaterialsAPI(Resource):
    def post(self, work_order_id):
        """Allocate materials for a work order"""
        try:
            transactions = MaterialTrackingService.allocate_materials_for_work_order(work_order_id, ERP_API_URL)
            if not transactions:
                return {'error': 'Failed to allocate materials'}, 400
            
            return transactions, 201
        except Exception as e:
            return {'error': str(e)}, 500
        
class MaterialListAPI(Resource):
    def get(self):
        try:
            materials = MaterialService.get_all_materials()
            return materials
        except Exception as e:
            return {'error': str(e)}, 500

    def post(self):
        try:
            material_data = request.get_json()
            if not material_data:
                return {'error': 'No data provided'}, 400
            
            material = MaterialService.create_material(material_data)
            return material, 201
        except Exception as e:
            return {'error': str(e)}, 500

class ConsumeMaterialsAPI(Resource):
    def post(self, work_order_id):
        """Consume materials for a work order"""
        try:
            transactions = MaterialTrackingService.consume_materials_for_work_order(work_order_id, ERP_API_URL)
            if not transactions:
                return {'error': 'Failed to consume materials'}, 400
            
            return transactions, 201
        except Exception as e:
            return {'error': str(e)}, 500

# Production Count API
class ProductionCountListAPI(Resource):
    def get(self):
        """Get all production counts"""
        try:
            counts = ProductionCountService.get_all_production_counts()
            return counts
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new production count"""
        try:
            count_data = request.get_json()
            if not count_data:
                return {'error': 'No data provided'}, 400
            
            count = ProductionCountService.create_production_count(count_data)
            return count, 201
        except Exception as e:
            return {'error': str(e)}, 500

class ProductionCountAPI(Resource):
    def get(self, count_id):
        """Get production count by ID"""
        try:
            count = ProductionCountService.get_production_count_by_id(count_id)
            if not count:
                return {'error': 'Production count not found'}, 404
            
            return count
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, count_id):
        """Update a production count"""
        try:
            count_data = request.get_json()
            if not count_data:
                return {'error': 'No data provided'}, 400
            
            count = ProductionCountService.update_production_count(count_id, count_data)
            if not count:
                return {'error': 'Production count not found'}, 404
            
            return count
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, count_id):
        """Delete a production count"""
        try:
            result = ProductionCountService.delete_production_count(count_id)
            if not result:
                return {'error': 'Production count not found'}, 404
            
            return {'message': 'Production count deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class ProductionCountsByWorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get production counts for a specific work order"""
        try:
            counts = ProductionCountService.get_production_counts_by_work_order(work_order_id)
            return counts
        except Exception as e:
            return {'error': str(e)}, 500

class ProductionSummaryByWorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get production summary for a specific work order"""
        try:
            summary = ProductionCountService.get_production_summary_by_work_order(work_order_id)
            return summary
        except Exception as e:
            return {'error': str(e)}, 500

class IncrementProductionCountAPI(Resource):
    def post(self, work_order_id):
        """Increment production count for a work order"""
        try:
            data = request.get_json() or {}
            good = data.get('good', 0)
            reject = data.get('reject', 0)
            rework = data.get('rework', 0)
            
            count = ProductionCountService.increment_production_count(work_order_id, good, reject, rework)
            return count, 201
        except Exception as e:
            return {'error': str(e)}, 500
        
class ProductionPlanListAPI(Resource):
    def get(self):
        return ProductionPlanService.get_all_plans()

    def post(self):
        data = request.get_json()
        plan = ProductionPlanService.create_plan(data)
        return plan, 201
    
class ProductionPlanAPI(Resource):
    def get(self, plan_id):
        plan = ProductionPlanService.get_plan_by_id(plan_id)
        if not plan:
            return {'error': 'Not found'}, 404
        return plan

    def put(self, plan_id):
        data = request.get_json()
        updated = ProductionPlanService.update_plan(plan_id, data)
        if not updated:
            return {'error': 'Not found'}, 404
        return updated

    def delete(self, plan_id):
        deleted = ProductionPlanService.delete_plan(plan_id)
        if not deleted:
            return {'error': 'Not found'}, 404
        return {'message': 'Deleted successfully'}
# Downtime API
class DowntimeListAPI(Resource):
    def get(self):
        """Get all downtimes"""
        try:
            downtimes = DowntimeService.get_all_downtimes()
            return downtimes
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new downtime"""
        try:
            downtime_data = request.get_json()
            if not downtime_data:
                return {'error': 'No data provided'}, 400
            
            downtime = DowntimeService.create_downtime(downtime_data)
            return downtime, 201
        except Exception as e:
            return {'error': str(e)}, 500

class DowntimeAPI(Resource):
    def get(self, downtime_id):
        """Get downtime by ID"""
        try:
            downtime = DowntimeService.get_downtime_by_id(downtime_id)
            if not downtime:
                return {'error': 'Downtime not found'}, 404
            
            return downtime
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, downtime_id):
        """Update a downtime"""
        try:
            downtime_data = request.get_json()
            if not downtime_data:
                return {'error': 'No data provided'}, 400
            
            downtime = DowntimeService.update_downtime(downtime_id, downtime_data)
            if not downtime:
                return {'error': 'Downtime not found'}, 404
            
            return downtime
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, downtime_id):
        """Delete a downtime"""
        try:
            result = DowntimeService.delete_downtime(downtime_id)
            if not result:
                return {'error': 'Downtime not found'}, 404
            
            return {'message': 'Downtime deleted successfully'}
        except Exception as e:
            return {'error': str(e)}, 500

class DowntimesByMachineAPI(Resource):
    def get(self, machine_id):
        """Get downtimes for a specific machine"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            downtimes = DowntimeService.get_downtimes_by_machine(machine_id, start_date, end_date)
            return downtimes
        except Exception as e:
            return {'error': str(e)}, 500

class ActiveDowntimesAPI(Resource):
    def get(self):
        """Get all active downtimes"""
        try:
            downtimes = DowntimeService.get_active_downtimes()
            return downtimes
        except Exception as e:
            return {'error': str(e)}, 500

class EndDowntimeAPI(Resource):
    def put(self, downtime_id):
        """End a downtime event"""
        try:
            downtime = DowntimeService.end_downtime(downtime_id)
            if not downtime:
                return {'error': 'Downtime not found or already ended'}, 404
            
            return downtime
        except Exception as e:
            return {'error': str(e)}, 500

# Register API resources
# Work Orders
api.add_resource(WorkOrderListAPI, f'{API_PREFIX}/work-orders')
api.add_resource(WorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>')
api.add_resource(WorkOrderByNumberAPI, f'{API_PREFIX}/work-orders/number/<string:work_order_number>')
api.add_resource(WorkOrderStatusAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/status')
api.add_resource(WorkOrdersByMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/work-orders')
api.add_resource(ActiveWorkOrdersAPI, f'{API_PREFIX}/work-orders/active')
api.add_resource(CompletedWorkOrdersAPI, f'{API_PREFIX}/work-orders/completed')

# Production Plans
api.add_resource(ProductionPlanListAPI, f'{API_PREFIX}/production-plans')  # GET all, POST new
api.add_resource(ProductionPlanAPI, f'{API_PREFIX}/production-plans/<int:plan_id>')  # GET/PUT/DELETE by ID

# Work Orders linked to a Production Plan
api.add_resource(WorkOrdersByProductionPlanAPI, f'{API_PREFIX}/production-plans/<int:production_plan_id>/work-orders')  # GET work orders
api.add_resource(GenerateWorkOrdersAPI, f'{API_PREFIX}/production-plans/<int:production_plan_id>/generate-work-orders')  # POST generate work orders



# Machines
api.add_resource(MachineListAPI, f'{API_PREFIX}/machines')
api.add_resource(MachineAPI, f'{API_PREFIX}/machines/<int:machine_id>')
api.add_resource(MachineByCodeAPI, f'{API_PREFIX}/machines/code/<string:machine_code>')
api.add_resource(MachineStatusAPI, f'{API_PREFIX}/machines/<int:machine_id>/status')
api.add_resource(AvailableMachinesAPI, f'{API_PREFIX}/machines/available')
api.add_resource(MachinesByTypeAPI, f'{API_PREFIX}/machines/type/<string:machine_type>')

# Production Schedule
api.add_resource(ScheduleListAPI, f'{API_PREFIX}/schedule')
api.add_resource(ScheduleEntryAPI, f'{API_PREFIX}/schedule/<int:entry_id>')
api.add_resource(MachineScheduleAPI, f'{API_PREFIX}/machines/<int:machine_id>/schedule')
api.add_resource(WorkOrderScheduleAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/schedule')
api.add_resource(MachineAvailabilityAPI, f'{API_PREFIX}/machines/<int:machine_id>/availability')
api.add_resource(AutoScheduleWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/auto-schedule')

# Quality Control
api.add_resource(QualityCheckListAPI, f'{API_PREFIX}/quality-checks')
api.add_resource(QualityCheckAPI, f'{API_PREFIX}/quality-checks/<int:check_id>')
api.add_resource(QualityChecksByWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/quality-checks')
api.add_resource(QualitySummaryByWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/quality-summary')

# Material Tracking
api.add_resource(MaterialTransactionListAPI, f'{API_PREFIX}/material-transactions')
api.add_resource(MaterialTransactionAPI, f'{API_PREFIX}/material-transactions/<int:transaction_id>')
api.add_resource(MaterialTransactionsByWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/material-transactions')
api.add_resource(MaterialTransactionsByMaterialAPI, f'{API_PREFIX}/materials/<int:material_id>/transactions')
api.add_resource(AllocateMaterialsAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/allocate-materials')
api.add_resource(ConsumeMaterialsAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/consume-materials')
# Material 
api.add_resource(MaterialAPI, f'{API_PREFIX}/materials/<int:material_id>')

api.add_resource(MaterialListAPI, f'{API_PREFIX}/materials')
api.add_resource(MaterialByCodeAPI, f'{API_PREFIX}/materials/code/<string:code>')


# Production Count
api.add_resource(ProductionCountListAPI, f'{API_PREFIX}/production-counts')
api.add_resource(ProductionCountAPI, f'{API_PREFIX}/production-counts/<int:count_id>')
api.add_resource(ProductionCountsByWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/production-counts')
api.add_resource(ProductionSummaryByWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/production-summary')
api.add_resource(IncrementProductionCountAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/increment-count')



# Downtime
api.add_resource(DowntimeListAPI, f'{API_PREFIX}/downtimes')
api.add_resource(DowntimeAPI, f'{API_PREFIX}/downtimes/<int:downtime_id>')
api.add_resource(DowntimesByMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/downtimes')
api.add_resource(ActiveDowntimesAPI, f'{API_PREFIX}/downtimes/active')
api.add_resource(EndDowntimeAPI, f'{API_PREFIX}/downtimes/<int:downtime_id>/end')

# Root endpoint
@app.route('/')
def index():
    return {
        'name': 'MES Emulator API',
        'version': api_version,
        'endpoints': [
            f'{API_PREFIX}/work-orders',
            f'{API_PREFIX}/machines',
            f'{API_PREFIX}/schedule',
            f'{API_PREFIX}/quality-checks',
            f'{API_PREFIX}/material-transactions',
            f'{API_PREFIX}/production-counts',
            f'{API_PREFIX}/downtimes',
            f'{API_PREFIX}/materials',
            f'{API_PREFIX}/status'
        ]
    }

def run_app():
    """Run the Flask application"""
    host = config['mes']['host']
    port = config['mes']['port']
    app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    run_app()

"""
PCS Emulator - API Endpoints
Provides REST API endpoints for the PCS emulator
"""
import os
import sys
import yaml
from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from dotenv import load_dotenv

# Load environment variables from project root .env
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, '.env'))

# Import shared auth utilities
sys.path.insert(0, os.path.join(_project_root, 'common'))
from auth import require_api_key, get_cors_origins  # noqa: E402
from services import (
    init_machine_manager, get_machine_manager,
    MachineParameterService, SensorDataService, AlarmService,
    MachineStateService, CycleDataService, MachineCommandService,
    MachineService, MESClient, WorkOrderService
)
from models import Base
from database import engine

# Ensure all tables exist (including cycle_data)
Base.metadata.create_all(engine)

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# Create Flask app
app = Flask(__name__)

# CORS configuration – restrict to configured origins (fixes issue #5)
_allowed_origins = get_cors_origins()

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '')
    if origin in _allowed_origins or '*' in _allowed_origins:
        response.headers.set('Access-Control-Allow-Origin', origin or _allowed_origins[0])
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-API-Key')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

api = Api(app)

# API version prefix
api_version = config['pcs']['api_version']
API_PREFIX = f"/api/{api_version}"

# Initialize machine simulator manager (fixes issue #13 – deferred from module-level
# so that importing this module in tests does not spin up background threads)
def _bootstrap():
    """Run once at server startup to initialise the machine simulator manager."""
    init_machine_manager(config)

_bootstrap()

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
    return {'status': 'ok', 'service': 'PCS'}, 200

# Register work order – persisted to DB via WorkOrderService (fixes issue #15)
@app.route('/api/v1/work-orders', methods=['POST'])
def register_work_order():
    data = request.get_json() or {}
    result, status_code = WorkOrderService.register_work_order(data)
    return result, status_code

@app.route('/api/v1/alarms/<int:alarm_id>/acknowledge', methods=['POST'])
@require_api_key  # fixes issue #6 – control endpoint requires API key
def acknowledge_alarm(alarm_id):
    alarm = AlarmService.acknowledge_alarm(alarm_id)
    if alarm:
        return alarm, 200
    return {'error': 'Alarm not found'}, 404

@app.route('/api/v1/alarms/<int:alarm_id>/resolve', methods=['POST'])
@require_api_key  # fixes issue #6 – control endpoint requires API key
def resolve_alarm(alarm_id):
    alarm = AlarmService.resolve_alarm(alarm_id)
    if alarm:
        return alarm, 200
    return {'error': 'Alarm not found'}, 404

#for  communicating  with MES    
@app.route('/api/v1/machines/cycles/completed', methods=['GET'])
def get_completed_cycles():
    try:
        completed_cycles = CycleDataService.get_completed_cycles()
        result = [{
            'id': cycle.id,
            'machine_id': cycle.machine_id,
            'work_order_id': cycle.work_order_id,
            'cycle_number': cycle.cycle_number,
            'cycle_time': cycle.cycle_time
        } for cycle in completed_cycles]

        return result, 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/api/v1/machines/cycles/<int:cycle_id>/mark-synced', methods=['POST'])
def mark_cycle_synced(cycle_id):
    try:
        success = CycleDataService.mark_cycle_as_synced(cycle_id)
        if success:
            return {'message': 'Cycle marked as synced'}, 200
        else:
            return {'error': 'Cycle not found'}, 404
    except Exception as e:
        return {'error': str(e)}, 500
    
# Machine Parameters API
class MachineParametersListAPI(Resource):
    def get(self):
        """Get all machine parameters"""
        try:
            parameters = MachineParameterService.get_all_parameters()
            return parameters
        except Exception as e:
            return {'error': str(e)}, 500

class MachineParametersByMachineAPI(Resource):
    def get(self, machine_id):
        """Get parameters for a specific machine"""
        try:
            parameters = MachineParameterService.get_parameters_by_machine(machine_id)
            return parameters
        except Exception as e:
            return {'error': str(e)}, 500

class MachineParameterAPI(Resource):
    def get(self, machine_id, parameter_name):
        """Get a specific parameter for a machine"""
        try:
            parameter = MachineParameterService.get_parameter(machine_id, parameter_name)
            if not parameter:
                return {'error': 'Parameter not found'}, 404
            
            return parameter
        except Exception as e:
            return {'error': str(e)}, 500
    
    def put(self, machine_id, parameter_name):
        """Update a machine parameter setpoint"""
        try:
            data = request.get_json()
            if not data or 'set_point' not in data:
                return {'error': 'No set_point provided'}, 400
            
            parameter = MachineParameterService.update_parameter(machine_id, parameter_name, data['set_point'])
            if not parameter:
                return {'error': 'Failed to update parameter'}, 400
            
            return parameter
        except Exception as e:
            return {'error': str(e)}, 500

# Sensor Data API
class SensorDataLatestAPI(Resource):
    def get(self, machine_id):
        """Get latest sensor data for a machine"""
        try:
            sensor_name = request.args.get('sensor_name')
            limit = request.args.get('limit', 100, type=int)
            
            data = SensorDataService.get_latest_sensor_data(machine_id, sensor_name, limit)
            return data
        except Exception as e:
            return {'error': str(e)}, 500

class SensorDataRangeAPI(Resource):
    def get(self, machine_id, sensor_name):
        """Get sensor data within a time range"""
        try:
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            limit = request.args.get('limit', 1000, type=int)
            
            if not start_time or not end_time:
                return {'error': 'Start time and end time are required'}, 400
            
            data = SensorDataService.get_sensor_data_in_range(machine_id, sensor_name, start_time, end_time, limit)
            return data
        except Exception as e:
            return {'error': str(e)}, 500

class SensorStatisticsAPI(Resource):
    def get(self, machine_id, sensor_name):
        """Get statistics for sensor data within a time range"""
        try:
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            
            if not start_time or not end_time:
                return {'error': 'Start time and end time are required'}, 400
            
            stats = SensorDataService.get_sensor_statistics(machine_id, sensor_name, start_time, end_time)
            return stats
        except Exception as e:
            return {'error': str(e)}, 500

# Alarms API
class AlarmsListAPI(Resource):
    def get(self):
        """Get all alarms"""
        try:
            include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
            alarms = AlarmService.get_all_alarms(include_resolved)
            return alarms
        except Exception as e:
            return {'error': str(e)}, 500
    
    def post(self):
        """Create a new alarm"""
        try:
            data = request.get_json()
            if not data or 'machine_id' not in data or 'alarm_code' not in data or 'description' not in data or 'severity' not in data:
                return {'error': 'Missing required fields'}, 400
            
            alarm = AlarmService.create_alarm(
                data['machine_id'],
                data['alarm_code'],
                data['description'],
                data['severity']
            )
            
            if not alarm:
                return {'error': 'Failed to create alarm'}, 400
            
            return alarm, 201
        except Exception as e:
            return {'error': str(e)}, 500

class AlarmsByMachineAPI(Resource):
    def get(self, machine_id):
        """Get alarms for a specific machine"""
        try:
            include_resolved = request.args.get('include_resolved', 'false').lower() == 'true'
            alarms = AlarmService.get_alarms_by_machine(machine_id, include_resolved)
            return alarms
        except Exception as e:
            return {'error': str(e)}, 500

class AlarmAPI(Resource):
    def get(self, alarm_id):
        """Get alarm by ID"""
        try:
            alarm = AlarmService.get_alarm_by_id(alarm_id)
            if not alarm:
                return {'error': 'Alarm not found'}, 404
            
            return alarm
        except Exception as e:
            return {'error': str(e)}, 500

class AlarmAcknowledgeAPI(Resource):
    def put(self, alarm_id):
        """Acknowledge an alarm"""
        try:
            alarm = AlarmService.acknowledge_alarm(alarm_id)
            if not alarm:
                return {'error': 'Alarm not found'}, 404
            
            return alarm
        except Exception as e:
            return {'error': str(e)}, 500

class AlarmResolveAPI(Resource):
    def put(self, alarm_id):
        """Resolve an alarm"""
        try:
            alarm = AlarmService.resolve_alarm(alarm_id)
            if not alarm:
                return {'error': 'Alarm not found'}, 404
            
            return alarm
        except Exception as e:
            return {'error': str(e)}, 500

# Machine State API
class MachineCurrentStateAPI(Resource):
    def get(self, machine_id):
        """Get current state for a machine"""
        try:
            state = MachineStateService.get_current_state(machine_id)
            if not state:
                return {'error': 'No current state found'}, 404
            
            return state
        except Exception as e:
            return {'error': str(e)}, 500

class MachineStatesAPI(Resource):
    def get(self, machine_id):
        """Get state history for a machine"""
        try:
            limit = request.args.get('limit', 100, type=int)
            states = MachineStateService.get_machine_states(machine_id, limit)
            return states
        except Exception as e:
            return {'error': str(e)}, 500

class MachineStateByIdAPI(Resource):
    def get(self, state_id):
        """Get state by ID"""
        try:
            state = MachineStateService.get_state_by_id(state_id)
            if not state:
                return {'error': 'State not found'}, 404
            
            return state
        except Exception as e:
            return {'error': str(e)}, 500

class MachineUptimeAPI(Resource):
    def get(self, machine_id):
        """Calculate machine uptime within a time range"""
        try:
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            
            if not start_time or not end_time:
                return {'error': 'Start time and end time are required'}, 400
            
            uptime = MachineStateService.get_machine_uptime(machine_id, start_time, end_time)
            return uptime
        except Exception as e:
            return {'error': str(e)}, 500

# Cycle Data API
class CyclesByMachineAPI(Resource):
    def get(self, machine_id):
        """Get cycles for a machine"""
        try:
            limit = request.args.get('limit', 100, type=int)
            cycles = CycleDataService.get_cycles_by_machine(machine_id, limit)
            return cycles
        except Exception as e:
            return {'error': str(e)}, 500

class CyclesByWorkOrderAPI(Resource):
    def get(self, work_order_id):
        """Get cycles for a work order"""
        try:
            limit = request.args.get('limit', 1000, type=int)
            cycles = CycleDataService.get_cycles_by_work_order(work_order_id, limit)
            return cycles
        except Exception as e:
            return {'error': str(e)}, 500

class CycleAPI(Resource):
    def get(self, cycle_id):
        """Get cycle by ID"""
        try:
            cycle = CycleDataService.get_cycle_by_id(cycle_id)
            if not cycle:
                return {'error': 'Cycle not found'}, 404
            
            return cycle
        except Exception as e:
            return {'error': str(e)}, 500

class CycleStatisticsAPI(Resource):
    def get(self, machine_id):
        """Get cycle statistics for a machine"""
        try:
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            
            stats = CycleDataService.get_cycle_statistics(machine_id, start_time, end_time)
            return stats
        except Exception as e:
            return {'error': str(e)}, 500

# Machine Command API
class CommandsByMachineAPI(Resource):
    def get(self, machine_id):
        """Get commands for a machine"""
        try:
            limit = request.args.get('limit', 100, type=int)
            commands = MachineCommandService.get_commands_by_machine(machine_id, limit)
            return commands
        except Exception as e:
            return {'error': str(e)}, 500

class CommandAPI(Resource):
    def get(self, command_id):
        """Get command by ID"""
        try:
            command = MachineCommandService.get_command_by_id(command_id)
            if not command:
                return {'error': 'Command not found'}, 404
            
            return command
        except Exception as e:
            return {'error': str(e)}, 500

class CreateCommandAPI(Resource):
    def post(self, machine_id):
        """Create a new command"""
        try:
            data = request.get_json()
            if not data or 'command_type' not in data:
                return {'error': 'Missing command_type'}, 400
            
            parameters = data.get('parameters')
            
            command = MachineCommandService.create_command(machine_id, data['command_type'], parameters)
            if not command:
                return {'error': 'Failed to create command'}, 400
            
            return command, 201
        except Exception as e:
            return {'error': str(e)}, 500

# Machine API
class MachineStatusAPI(Resource):
    def get(self, machine_id):
        """Get current status of a machine"""
        try:
            status = MachineService.get_machine_status(machine_id)
            if not status:
                return {'error': 'Machine not found'}, 404
            
            return status
        except Exception as e:
            return {'error': str(e)}, 500

class AllMachinesStatusAPI(Resource):
    def get(self):
        """Get status of all machines"""
        try:
            status = MachineService.get_all_machines_status()
            return status
        except Exception as e:
            return {'error': str(e)}, 500

class CreateMachineAPI(Resource):
    def post(self):
        """Create a new machine simulator"""
        try:
            data = request.get_json()
            if not data or 'machine_id' not in data:
                return {'error': 'Missing machine_id'}, 400
            
            result = MachineService.create_machine(data['machine_id'])
            if not result:
                return {'error': 'Failed to create machine'}, 400
            
            return {'message': f"Machine {data['machine_id']} created successfully"}, 201
        except Exception as e:
            return {'error': str(e)}, 500

class MESWorkOrderFetchAPI(Resource):
    def get(self, work_order_id):
        work_order = MESClient.get_work_order(work_order_id)
        if not work_order:
            return {'error': 'Work order not found'}, 404
        return work_order, 200


class WorkOrderAPI(Resource):
    def post(self):
        """Create a new work order"""
        data = request.get_json()  # Get the data from the request body
        
        # Call the service method to register the work order
        result, status_code = WorkOrderService.register_work_order(data)
        
        return result, status_code


# PCSWorkOrderStore removed – work orders are now persisted to the database
# via WorkOrderService.register_work_order() (fixes issue #15)

class StartMachineAPI(Resource):
    @require_api_key  # fixes issue #6 – machine control requires API key
    def post(self, machine_id):
        """Start a machine"""
        try:
            data = request.get_json() or {}
            work_order_id = data.get('work_order_id')
            
            command = MachineService.start_machine(machine_id, work_order_id)
            if not command:
                return {'error': 'Failed to start machine'}, 400
            
            return command, 200
        except Exception as e:
            return {'error': str(e)}, 500

class StopMachineAPI(Resource):
    @require_api_key  # fixes issue #6 – machine control requires API key
    def post(self, machine_id):
        """Stop a machine"""
        try:
            command = MachineService.stop_machine(machine_id)
            if not command:
                return {'error': 'Failed to stop machine'}, 400
            
            return command, 200
        except Exception as e:
            return {'error': str(e)}, 500

class SetMachineParameterAPI(Resource):
    @require_api_key  # fixes issue #6 – machine control requires API key
    def post(self, machine_id):
        """Set a machine parameter"""
        try:
            data = request.get_json()
            if not data or 'parameter_name' not in data or 'value' not in data:
                return {'error': 'Missing parameter_name or value'}, 400
            
            command = MachineService.set_machine_parameter(machine_id, data['parameter_name'], data['value'])
            if not command:
                return {'error': 'Failed to set parameter'}, 400
            
            return command, 200
        except Exception as e:
            return {'error': str(e)}, 500

# Register API resources
# Machine Parameters
api.add_resource(MachineParametersListAPI, f'{API_PREFIX}/parameters')
api.add_resource(MachineParametersByMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/parameters')
api.add_resource(MachineParameterAPI, f'{API_PREFIX}/machines/<int:machine_id>/parameters/<string:parameter_name>')

# Sensor Data
api.add_resource(SensorDataLatestAPI, f'{API_PREFIX}/machines/<int:machine_id>/sensors')
api.add_resource(SensorDataRangeAPI, f'{API_PREFIX}/machines/<int:machine_id>/sensors/<string:sensor_name>/range')
api.add_resource(SensorStatisticsAPI, f'{API_PREFIX}/machines/<int:machine_id>/sensors/<string:sensor_name>/statistics')

# Alarms
api.add_resource(AlarmsListAPI, f'{API_PREFIX}/alarms')
api.add_resource(AlarmsByMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/alarms')
api.add_resource(AlarmAPI, f'{API_PREFIX}/alarms/<int:alarm_id>')
api.add_resource(AlarmAcknowledgeAPI, f'{API_PREFIX}/alarms/<int:alarm_id>/acknowledge')
api.add_resource(AlarmResolveAPI, f'{API_PREFIX}/alarms/<int:alarm_id>/resolve')

# Machine States
api.add_resource(MachineCurrentStateAPI, f'{API_PREFIX}/machines/<int:machine_id>/state')
api.add_resource(MachineStatesAPI, f'{API_PREFIX}/machines/<int:machine_id>/states')
api.add_resource(MachineStateByIdAPI, f'{API_PREFIX}/states/<int:state_id>')
api.add_resource(MachineUptimeAPI, f'{API_PREFIX}/machines/<int:machine_id>/uptime')

# Cycle Data
api.add_resource(CyclesByMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/cycles')
api.add_resource(CyclesByWorkOrderAPI, f'{API_PREFIX}/work-orders/<int:work_order_id>/cycles')
api.add_resource(CycleAPI, f'{API_PREFIX}/cycles/<int:cycle_id>')
api.add_resource(CycleStatisticsAPI, f'{API_PREFIX}/machines/<int:machine_id>/cycle-statistics')

# Machine Commands
api.add_resource(CommandsByMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/commands')
api.add_resource(CommandAPI, f'{API_PREFIX}/commands/<int:command_id>')
api.add_resource(CreateCommandAPI, f'{API_PREFIX}/machines/<int:machine_id>/commands')

# Machine Management
api.add_resource(MachineStatusAPI, f'{API_PREFIX}/machines/<int:machine_id>/status')
api.add_resource(AllMachinesStatusAPI, f'{API_PREFIX}/machines/status')
api.add_resource(CreateMachineAPI, f'{API_PREFIX}/machines')
api.add_resource(StartMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/start')
api.add_resource(StopMachineAPI, f'{API_PREFIX}/machines/<int:machine_id>/stop')
api.add_resource(SetMachineParameterAPI, f'{API_PREFIX}/machines/<int:machine_id>/set-parameter')
#Messy entry point for MES work orders
api.add_resource(MESWorkOrderFetchAPI, f"{API_PREFIX}/mes/work-orders/<int:work_order_id>")
api.add_resource(WorkOrderAPI, f"{API_PREFIX}/work-orders")


# Root endpoint
@app.route('/')
def index():
    return {
        'name': 'PCS Emulator API',
        'version': api_version,
        'endpoints': [
            f'{API_PREFIX}/machines',
            f'{API_PREFIX}/parameters',
            f'{API_PREFIX}/alarms',
            f'{API_PREFIX}/cycles',
            f'{API_PREFIX}/status'
        ]
    }

def run_app():
    """Run the Flask application"""
    host = config['pcs']['host']
    port = config['pcs']['port']
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_app()

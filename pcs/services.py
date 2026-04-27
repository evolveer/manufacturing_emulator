"""
PCS Emulator - Service Layer
Provides business logic for the PCS emulator
"""
import datetime
import json
import logging
import os
import requests
from sqlalchemy.exc import SQLAlchemyError
from database import get_db_session, close_db_session
from models import MachineParameter, SensorData, Alarm, MachineState, CycleData, MachineCommand, WorkOrder
from machine_simulator import MachineSimulatorManager

logger = logging.getLogger('pcs_emulator.services')

# Global machine simulator manager
machine_manager = None

# MES URL – read from environment or fall back to config default (fixes issue #2)
_MES_URL = os.environ.get('MES_URL', 'http://localhost:5002/api/v1').rstrip('/')

def init_machine_manager(config):
    """Initialize the machine simulator manager"""
    global machine_manager, _MES_URL
    if machine_manager is None:
        machine_manager = MachineSimulatorManager(config)
    # Allow config to override MES URL if env var not set
    if not os.environ.get('MES_URL'):
        _mes_cfg = config.get('pcs', {}).get('mes_connection', {})
        _MES_URL = _mes_cfg.get('url', _MES_URL).rstrip('/')
    return machine_manager

def get_machine_manager():
    """Get the machine simulator manager"""
    global machine_manager
    return machine_manager

class MachineParameterService:
    """Service for machine parameter management"""
    
    @staticmethod
    def get_all_parameters():
        """Get all machine parameters"""
        session = get_db_session()
        try:
            parameters = session.query(MachineParameter).all()
            return [param.to_dict() for param in parameters]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_parameters_by_machine(machine_id):
        """Get parameters for a specific machine"""
        session = get_db_session()
        try:
            parameters = session.query(MachineParameter).filter(
                MachineParameter.machine_id == machine_id
            ).all()
            return [param.to_dict() for param in parameters]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_parameter(machine_id, parameter_name):
        """Get a specific parameter for a machine"""
        session = get_db_session()
        try:
            parameter = session.query(MachineParameter).filter(
                MachineParameter.machine_id == machine_id,
                MachineParameter.parameter_name == parameter_name
            ).first()
            return parameter.to_dict() if parameter else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_parameter(machine_id, parameter_name, set_point):
        """Update a machine parameter setpoint"""
        # Update in simulator
        manager = get_machine_manager()
        if manager:
            result = manager.set_machine_parameter(machine_id, parameter_name, set_point)
            if not result:
                return None
        
        # Update in database
        session = get_db_session()
        try:
            parameter = session.query(MachineParameter).filter(
                MachineParameter.machine_id == machine_id,
                MachineParameter.parameter_name == parameter_name
            ).first()
            
            if not parameter:
                return None
            
            parameter.set_point = set_point
            session.commit()
            return parameter.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating parameter: {str(e)}")
            return None
        finally:
            close_db_session(session)


class SensorDataService:
    """Service for sensor data management"""
    
    @staticmethod
    def get_latest_sensor_data(machine_id, sensor_name=None, limit=100):
        """Get latest sensor data for a machine"""
        session = get_db_session()
        try:
            query = session.query(SensorData).filter(
                SensorData.machine_id == machine_id
            )
            
            if sensor_name:
                query = query.filter(SensorData.sensor_name == sensor_name)
            
            data = query.order_by(SensorData.timestamp.desc()).limit(limit).all()
            return [item.to_dict() for item in data]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_sensor_data_in_range(machine_id, sensor_name, start_time, end_time, limit=1000):
        """Get sensor data within a time range"""
        session = get_db_session()
        try:
            data = session.query(SensorData).filter(
                SensorData.machine_id == machine_id,
                SensorData.sensor_name == sensor_name,
                SensorData.timestamp >= start_time,
                SensorData.timestamp <= end_time
            ).order_by(SensorData.timestamp).limit(limit).all()
            
            return [item.to_dict() for item in data]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_sensor_statistics(machine_id, sensor_name, start_time, end_time):
        """Get statistics for sensor data within a time range"""
        session = get_db_session()
        try:
            data = session.query(SensorData).filter(
                SensorData.machine_id == machine_id,
                SensorData.sensor_name == sensor_name,
                SensorData.timestamp >= start_time,
                SensorData.timestamp <= end_time
            ).all()
            
            if not data:
                return {
                    'machine_id': machine_id,
                    'sensor_name': sensor_name,
                    'count': 0,
                    'min': None,
                    'max': None,
                    'avg': None,
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None
                }
            
            values = [item.value for item in data]
            
            return {
                'machine_id': machine_id,
                'sensor_name': sensor_name,
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None
            }
        finally:
            close_db_session(session)


class AlarmService:
    """Service for alarm management"""
    
    @staticmethod
    def get_all_alarms(include_resolved=False):
        """Get all alarms"""
        session = get_db_session()
        try:
            query = session.query(Alarm)
            
            if not include_resolved:
                query = query.filter(Alarm.status != 'resolved')
            
            alarms = query.order_by(Alarm.start_time.desc()).all()
            return [alarm.to_dict() for alarm in alarms]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_alarms_by_machine(machine_id, include_resolved=False):
        """Get alarms for a specific machine"""
        session = get_db_session()
        try:
            query = session.query(Alarm).filter(
                Alarm.machine_id == machine_id
            )
            
            if not include_resolved:
                query = query.filter(Alarm.status != 'resolved')
            
            alarms = query.order_by(Alarm.start_time.desc()).all()
            return [alarm.to_dict() for alarm in alarms]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_alarm_by_id(alarm_id):
        """Get alarm by ID"""
        session = get_db_session()
        try:
            alarm = session.query(Alarm).filter(Alarm.id == alarm_id).first()
            return alarm.to_dict() if alarm else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def acknowledge_alarm(alarm_id):
        """Acknowledge an alarm"""
        session = get_db_session()
        try:
            alarm = session.query(Alarm).filter(Alarm.id == alarm_id).first()
            if not alarm:
                return None
            
            alarm.acknowledged = True
            alarm.status = 'acknowledged'
            session.commit()
            return alarm.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error acknowledging alarm: {str(e)}")
            return None
        finally:
            close_db_session(session)
    
    @staticmethod
    def resolve_alarm(alarm_id):
        """Resolve an alarm"""
        session = get_db_session()
        try:
            alarm = session.query(Alarm).filter(Alarm.id == alarm_id).first()
            if not alarm:
                return None
            
            alarm.status = 'resolved'
            alarm.end_time = datetime.datetime.utcnow()
            session.commit()
            return alarm.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error resolving alarm: {str(e)}")
            return None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_alarm(machine_id, alarm_code, description, severity):
        """Create a new alarm"""
        session = get_db_session()
        try:
            alarm = Alarm(
                machine_id=machine_id,
                alarm_code=alarm_code,
                description=description,
                severity=severity,
                status='active',
                start_time=datetime.datetime.utcnow(),
                acknowledged=False
            )
            session.add(alarm)
            session.commit()
            return alarm.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating alarm: {str(e)}")
            return None
        finally:
            close_db_session(session)


class MachineStateService:
    """Service for machine state management"""
    
    @staticmethod
    def get_current_state(machine_id):
        """Get current state for a machine"""
        session = get_db_session()
        try:
            state = session.query(MachineState).filter(
                MachineState.machine_id == machine_id,
                MachineState.end_time == None
            ).first()
            return state.to_dict() if state else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_machine_states(machine_id, limit=100):
        """Get state history for a machine"""
        session = get_db_session()
        try:
            states = session.query(MachineState).filter(
                MachineState.machine_id == machine_id
            ).order_by(MachineState.start_time.desc()).limit(limit).all()
            return [state.to_dict() for state in states]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_state_by_id(state_id):
        """Get state by ID"""
        session = get_db_session()
        try:
            state = session.query(MachineState).filter(MachineState.id == state_id).first()
            return state.to_dict() if state else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_machine_uptime(machine_id, start_time, end_time):
        """Calculate machine uptime within a time range"""
        session = get_db_session()
        try:
            states = session.query(MachineState).filter(
                MachineState.machine_id == machine_id,
                MachineState.start_time < end_time,
                (MachineState.end_time > start_time) | (MachineState.end_time == None)
            ).all()
            
            total_seconds = (end_time - start_time).total_seconds()
            running_seconds = 0
            idle_seconds = 0
            error_seconds = 0
            maintenance_seconds = 0
            setup_seconds = 0
            
            for state in states:
                # Calculate overlap with requested time range
                state_start = max(state.start_time, start_time)
                state_end = min(state.end_time or end_time, end_time)
                
                if state_end > state_start:
                    duration = (state_end - state_start).total_seconds()
                    
                    if state.state == 'running':
                        running_seconds += duration
                    elif state.state == 'idle':
                        idle_seconds += duration
                    elif state.state == 'error':
                        error_seconds += duration
                    elif state.state == 'maintenance':
                        maintenance_seconds += duration
                    elif state.state == 'setup':
                        setup_seconds += duration
            
            return {
                'machine_id': machine_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_seconds': total_seconds,
                'running_seconds': running_seconds,
                'idle_seconds': idle_seconds,
                'error_seconds': error_seconds,
                'maintenance_seconds': maintenance_seconds,
                'setup_seconds': setup_seconds,
                'uptime_percentage': (running_seconds / total_seconds * 100) if total_seconds > 0 else 0,
                'availability_percentage': ((running_seconds + idle_seconds + setup_seconds) / total_seconds * 100) if total_seconds > 0 else 0
            }
        finally:
            close_db_session(session)
            
    @staticmethod    
    def update_machine_state(machine_id, new_state):
        session = get_db_session()
        try:
            machine_state = session.query(MachineState).filter(
                MachineState.machine_id == machine_id,
                MachineState.end_time == None  # Find the latest active state
            ).first()

            if machine_state:
                machine_state.state = new_state
                session.commit()
            else:
                raise ValueError(f"No active state found for machine {machine_id}")
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)



class CycleDataService:
    """Service for cycle data management"""
    
    @staticmethod
    def get_cycles_by_machine(machine_id, limit=100):
        """Get cycles for a machine"""
        session = get_db_session()
        try:
            cycles = session.query(CycleData).filter(
                CycleData.machine_id == machine_id
            ).order_by(CycleData.start_time.desc()).limit(limit).all()
            return [cycle.to_dict() for cycle in cycles]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_cycles_by_work_order(work_order_id, limit=1000):
        """Get cycles for a work order"""
        session = get_db_session()
        try:
            cycles = session.query(CycleData).filter(
                CycleData.work_order_id == work_order_id
            ).order_by(CycleData.start_time).limit(limit).all()
            return [cycle.to_dict() for cycle in cycles]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_cycle_by_id(cycle_id):
        """Get cycle by ID"""
        session = get_db_session()
        try:
            cycle = session.query(CycleData).filter(CycleData.id == cycle_id).first()
            return cycle.to_dict() if cycle else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_cycle_statistics(machine_id, start_time=None, end_time=None):
        """Get cycle statistics for a machine"""
        session = get_db_session()
        try:
            query = session.query(CycleData).filter(
                CycleData.machine_id == machine_id
            )
            
            if start_time:
                query = query.filter(CycleData.start_time >= start_time)
            
            if end_time:
                query = query.filter(CycleData.start_time <= end_time)
            
            cycles = query.all()
            
            if not cycles:
                return {
                    'machine_id': machine_id,
                    'cycle_count': 0,
                    'completed_count': 0,
                    'aborted_count': 0,
                    'error_count': 0,
                    'avg_cycle_time': None,
                    'min_cycle_time': None,
                    'max_cycle_time': None
                }
            
            completed_cycles = [c for c in cycles if c.status == 'completed']
            aborted_cycles = [c for c in cycles if c.status == 'aborted']
            error_cycles = [c for c in cycles if c.status == 'error']
            
            cycle_times = [c.cycle_time for c in completed_cycles if c.cycle_time is not None]
            
            return {
                'machine_id': machine_id,
                'cycle_count': len(cycles),
                'completed_count': len(completed_cycles),
                'aborted_count': len(aborted_cycles),
                'error_count': len(error_cycles),
                'avg_cycle_time': sum(cycle_times) / len(cycle_times) if cycle_times else None,
                'min_cycle_time': min(cycle_times) if cycle_times else None,
                'max_cycle_time': max(cycle_times) if cycle_times else None,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None
            }
        finally:
            close_db_session(session)
            
            
    @staticmethod
    def get_completed_cycles():
        session = get_db_session()
        try:
            cycles = session.query(CycleData).filter(
                CycleData.status == 'ready_for_sync'
            ).all()
            return cycles
        finally:
            close_db_session(session)

    @staticmethod
    def mark_cycle_as_synced(cycle_id):
        session = get_db_session()
        try:
            cycle = session.query(CycleData).filter(
                CycleData.id == cycle_id
            ).first()
            if cycle:
                cycle.status = 'synced'
                cycle.synced_at = datetime.datetime.utcnow()
                session.commit()
                return True
            else:
                return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
            
                    
class MESClient:
    """Service for interacting with the MES system"""
    @staticmethod
    def get_work_order(work_order_id):
        try:
            response = requests.get(f"{_MES_URL}/work-orders/{work_order_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"MES returned {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to fetch work order from MES: {e}")
        return None

class MachineCommandService:
    """Service for machine command management"""
    
    @staticmethod
    def get_commands_by_machine(machine_id, limit=100):
        """Get commands for a machine"""
        session = get_db_session()
        try:
            commands = session.query(MachineCommand).filter(
                MachineCommand.machine_id == machine_id
            ).order_by(MachineCommand.timestamp.desc()).limit(limit).all()
            return [command.to_dict() for command in commands]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_command_by_id(command_id):
        """Get command by ID"""
        session = get_db_session()
        try:
            command = session.query(MachineCommand).filter(MachineCommand.id == command_id).first()
            return command.to_dict() if command else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_command(machine_id, command_type, parameters=None):
        """Create a new command"""
        session = get_db_session()
        try:
            command = MachineCommand(
                machine_id=machine_id,
                command_type=command_type,
                parameters=json.dumps(parameters) if parameters else None,
                timestamp=datetime.datetime.utcnow(),
                status='pending'
            )
            session.add(command)
            session.flush()
            command_id = command.id
            session.commit()
            logger.debug(f"Creating command '{command_type}' for machine {machine_id} with parameters: {parameters}")

            # Execute command
            result = MachineCommandService._execute_command(machine_id, command_id, command_type, parameters)
            logger.debug(f"Result from execute_command: {result}")

            return result
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating command: {str(e)}")
            return None
        finally:
            close_db_session(session)
    
    @staticmethod
    def _execute_command(machine_id, command_id, command_type, parameters):
        """Execute a command on the machine simulator"""
        manager = get_machine_manager()
        if not manager:
            MachineCommandService._update_command_status(command_id, 'failed', 'Machine manager not initialized')
            return None
        
        try:
            
            if command_type == 'start':
                work_order_id = parameters.get('work_order_id') if parameters else None
                logger.debug(f"Attempting to start machine {machine_id} with work_order_id {work_order_id}")

                if not work_order_id:
                    MachineCommandService._update_command_status(command_id, 'failed', 'Missing work_order_id')
                    return None

                # 🔎 Fetch the work order from MES
                work_order = MESClient.get_work_order(work_order_id)
                if not work_order:
                    MachineCommandService._update_command_status(command_id, 'failed', f'Work order {work_order_id} not found in MES')
                    return None

                # Optionally validate machine_id matches (if needed)
                if int(work_order.get("machine_id", -1)) != machine_id:
                    MachineCommandService._update_command_status(
                        command_id, 
                        'failed', 
                        f"Machine ID mismatch: MES assigned {work_order.get('machine_id')} but command was for {machine_id}"
                    )
                    return None

                # 🚀 Start the machine
                result = manager.start_machine(machine_id, work_order_id)
                logger.debug(f"Start result for machine {machine_id}: {result}")

                if result:
                    MachineCommandService._update_command_status(command_id, 'executed', 'Machine started successfully')
                else:
                    MachineCommandService._update_command_status(command_id, 'failed', 'Failed to start machine')

                
            
            elif command_type == 'stop':
                result = manager.stop_machine(machine_id)
                if result:
                    MachineCommandService._update_command_status(command_id, 'executed', 'Machine stopped successfully')
                else:
                    MachineCommandService._update_command_status(command_id, 'failed', 'Failed to stop machine')
            
            elif command_type == 'parameter_change':
                if not parameters or 'parameter_name' not in parameters or 'value' not in parameters:
                    MachineCommandService._update_command_status(command_id, 'failed', 'Missing parameter_name or value')
                    return None
                
                result = manager.set_machine_parameter(
                    machine_id, 
                    parameters['parameter_name'], 
                    parameters['value']
                )
                
                if result:
                    MachineCommandService._update_command_status(
                        command_id, 
                        'executed', 
                        f"Parameter {parameters['parameter_name']} set to {parameters['value']}"
                    )
                else:
                    MachineCommandService._update_command_status(
                        command_id, 
                        'failed', 
                        f"Failed to set parameter {parameters['parameter_name']}"
                    )
            
            else:
                MachineCommandService._update_command_status(command_id, 'failed', f"Unknown command type: {command_type}")
                return None
            
            # Get updated command
            return MachineCommandService.get_command_by_id(command_id)
        
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            MachineCommandService._update_command_status(command_id, 'failed', f"Error: {str(e)}")
            return None
    
    @staticmethod
    def _update_command_status(command_id, status, response=None):
        """Update command status in database"""
        session = get_db_session()
        try:
            command = session.query(MachineCommand).filter(MachineCommand.id == command_id).first()
            if command:
                command.status = status
                command.response = response
                session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating command status: {str(e)}")
        finally:
            close_db_session(session)
            
class MachineStateService:
    """Service for machine state management"""
    
    @staticmethod
    def create_initial_state(machine_id):
        """Create initial machine state as idle"""
        session = get_db_session()
        try:
            state = MachineState(
                machine_id=machine_id,
                state='idle',  # Initial state is set to 'idle'
                start_time=datetime.datetime.utcnow(),
                cycle_count=0  # Set cycle count to 0 initially
            )
            session.add(state)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating initial machine state: {str(e)}")
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_current_state(machine_id):
        """Get the current state of a machine (the one without an end_time)"""
        session = get_db_session()
        try:
            # Fetch the machine's most recent state that has no end_time
            state = session.query(MachineState).filter(
                MachineState.machine_id == machine_id,
                MachineState.end_time == None  # Ensure it's the current state
            ).first()

            return state.to_dict() if state else None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching current state for machine {machine_id}: {str(e)}")
            return None
        finally:
            close_db_session(session)
            
class WorkOrderService:
    """Service for work order management"""
    
    @staticmethod
    def get_all_work_orders():
        """Get all work orders"""
        session = get_db_session()
        try:
            work_orders = session.query(WorkOrder).all()
            return [work_order.to_dict() for work_order in work_orders]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_work_order_by_id(work_order_id):
        """Get a work order by ID"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            return work_order.to_dict() if work_order else None
        finally:
            close_db_session(session)

    @staticmethod
    def register_work_order(data):
        """Register a new work order"""
        # Make sure the data contains all required fields
        required_fields = ['work_order_number', 'production_plan_id', 'product_id', 'quantity', 'status']
        for field in required_fields:
            if field not in data:
                return {'error': f'Missing required field: {field}'}, 400

        # Create the work order object
        work_order = WorkOrder(
            work_order_number=data['work_order_number'],
            production_plan_id=data['production_plan_id'],
            product_id=data['product_id'],
            quantity=data['quantity'],
            status=data['status']
        )
        
        # Persist to the database
        session = get_db_session()
        try:
            session.add(work_order)
            session.commit()  # Commit changes to the database
            return {'message': 'Work order registered', 'work_order': work_order.to_dict()}, 201
        except Exception as e:
            session.rollback()  # Rollback on failure
            return {'error': str(e)}, 500
        finally:
            close_db_session(session)


class MachineService:
    """Service for machine management"""
    
    @staticmethod
    def get_machine_status(machine_id):
        """Get current status of a machine"""
        # Get status from simulator
        manager = get_machine_manager()
        if manager:
            simulator_status = manager.get_machine_status(machine_id)
            if simulator_status:
                return simulator_status
        
        # If simulator not available, build status from database
        current_state = MachineStateService.get_current_state(machine_id)
        parameters = MachineParameterService.get_parameters_by_machine(machine_id)
        active_alarms = AlarmService.get_alarms_by_machine(machine_id, include_resolved=False)
        
        return {
            'machine_id': machine_id,
            'state': current_state['state'] if current_state else 'unknown',
            'parameters': {p['parameter_name']: p['current_value'] for p in parameters},
            'alarms': len(active_alarms),
            'work_order_id': current_state['work_order_id'] if current_state else None,
            'cycle_count': current_state['cycle_count'] if current_state else 0,
            'since': current_state['start_time'] if current_state else None
        }
    
    @staticmethod
    def get_all_machines_status():
        """Get status of all machines"""
        # Get status from simulator
        manager = get_machine_manager()
        if manager:
            return manager.get_all_machines_status()
        
        # If simulator not available, return empty dict
        return {}
    
    @staticmethod
    def create_machine(machine_id):
        """Create a new machine simulator"""
        manager = get_machine_manager()
        if not manager:
            return False
        
        # Create the machine in the simulator
        result = manager.create_machine(machine_id)
        
        if result:
            # Create an initial machine state as 'idle' after the machine is created
            MachineStateService.create_initial_state(machine_id)
        
        return result
    
    @staticmethod
    def start_machine(machine_id, work_order_id=None):
        """Start a machine"""
        logger.info("Starting machine %s with work order %s", machine_id, work_order_id)
        return MachineCommandService.create_command(
            machine_id, 
            'start', 
            {'work_order_id': work_order_id} if work_order_id else None
        )
    
    @staticmethod
    def stop_machine(machine_id):
        """Stop a machine"""
        return MachineCommandService.create_command(machine_id, 'stop')
    
    @staticmethod
    def set_machine_parameter(machine_id, parameter_name, value):
        """Set a machine parameter"""
        return MachineCommandService.create_command(
            machine_id, 
            'parameter_change', 
            {'parameter_name': parameter_name, 'value': value}
        )

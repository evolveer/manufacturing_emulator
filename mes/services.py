"""
MES Emulator - Service Layer
Provides business logic for the MES emulator
"""
import datetime
import uuid
import requests
from flask_restful import Resource
from sqlalchemy.exc import SQLAlchemyError
from database import get_db_session, close_db_session
from models import WorkOrder, Machine, ProductionSchedule, QualityCheck, MaterialTracking, ProductionCount, Downtime,Material,ProductionPlan

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
        """Get work order by ID"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            return work_order.to_dict() if work_order else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_work_order_by_number(work_order_number):
        """Get work order by work order number"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.work_order_number == work_order_number).first()
            return work_order.to_dict() if work_order else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_work_order(work_order_data):
        """Create a new work order"""
        session = get_db_session()
        try:
            # Generate work order number if not provided
            if 'work_order_number' not in work_order_data:
                work_order_data['work_order_number'] = f"WO-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            work_order = WorkOrder(
                work_order_number=work_order_data['work_order_number'],
                production_plan_id=work_order_data['production_plan_id'],
                product_id=work_order_data['product_id'],
                quantity=work_order_data['quantity'],
                status=work_order_data.get('status', 'planned'),
                start_time=work_order_data.get('start_time'),
                end_time=work_order_data.get('end_time'),
                machine_id=work_order_data.get('machine_id')
            )
            session.add(work_order)
            session.commit()
            return work_order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_work_order(work_order_id, work_order_data):
        """Update an existing work order"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            if not work_order:
                return None
            
            # Update fields
            for key, value in work_order_data.items():
                if hasattr(work_order, key) and key not in ['id', 'created_at', 'updated_at']:
                    setattr(work_order, key, value)
            
            session.commit()
            return work_order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_work_order(work_order_id):
        """Delete a work order"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            if not work_order:
                return False
            
            session.delete(work_order)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def mark_inventory_posted(work_order_id):
        """Flag a work order as already posted to ERP inventory"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            if not work_order:
                return None
            work_order.inventory_posted = True
            session.commit()
            return work_order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def update_work_order_status(work_order_id, status):
        """Update work order status"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            if not work_order:
                return None
            
            old_status = work_order.status
            work_order.status = status
            
            # Update timestamps based on status changes
            if status == 'in_progress' and old_status != 'in_progress':
                work_order.start_time = datetime.datetime.utcnow()
            elif status in ['completed', 'cancelled'] and old_status not in ['completed', 'cancelled']:
                work_order.end_time = datetime.datetime.utcnow()
            
            session.commit()
            return work_order.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    @staticmethod
    def get_work_orders_by_production_plan(production_plan_id):
        session = get_db_session()
        try:
            work_orders = session.query(WorkOrder).filter(WorkOrder.production_plan_id == production_plan_id).all()
            return [wo.to_dict() for wo in work_orders]
        finally:
            close_db_session(session)
            
    @staticmethod
    def get_work_orders_by_machine(machine_id):
        """Get work orders for a specific machine"""
        session = get_db_session()
        try:
            work_orders = session.query(WorkOrder).filter(WorkOrder.machine_id == machine_id).all()
            return [work_order.to_dict() for work_order in work_orders]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_active_work_orders():
        """Get all active work orders (planned, scheduled, in_progress)"""
        session = get_db_session()
        try:
            work_orders = session.query(WorkOrder).filter(
                WorkOrder.status.in_(['planned', 'scheduled', 'in_progress'])
            ).all()
            return [work_order.to_dict() for work_order in work_orders]
        finally:
            close_db_session(session)
            
    @staticmethod
    def get_completed_work_orders():
        """Get all completed work orders"""
        session = get_db_session()
        try:
            work_orders = session.query(WorkOrder).filter(WorkOrder.status == 'completed').all()
            result = []
            for wo in work_orders:
                result.append({
                    'id': wo.id,
                    'work_order_number': wo.work_order_number,
                    'quantity': wo.quantity,
                    'product_id': wo.product_id,
                    'production_plan_id': wo.production_plan_id,
                    'start_time': wo.start_time.isoformat() if wo.start_time else None,
                    'end_time': wo.end_time.isoformat() if wo.end_time else None
                })
        finally:
            close_db_session(session)
    
    
    @staticmethod
    def create_work_order_from_production_plan(production_plan_id, erp_api_url):
        """Create a work order from a production plan in the ERP system"""
        try:
            # Get production plan from ERP
            response = requests.get(f"{erp_api_url}/production-plans/{production_plan_id}")
            if response.status_code != 200:
                return None
            
            production_plan = response.json()
            
            # Get order details from ERP
            order_response = requests.get(f"{erp_api_url}/orders/{production_plan['order_id']}")
            if order_response.status_code != 200:
                return None
            
            order = order_response.json()
            
            # Create work orders for each order item
            work_orders = []
            for item in order['items']:
                work_order_data = {
                    'work_order_number': f"WO-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
                    'production_plan_id': production_plan_id,
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'status': 'planned'
                }
                work_order = WorkOrderService.create_work_order(work_order_data)
                work_orders.append(work_order)
            
            return work_orders
        except Exception as e:
            raise e
    @staticmethod
    def get_work_orders_by_plan(production_plan_id):
        """Get all work orders associated with a production plan"""
        session = get_db_session()
        try:
            work_orders = session.query(WorkOrder).filter(
                WorkOrder.production_plan_id == production_plan_id
            ).all()
            return [wo.to_dict() for wo in work_orders]
        finally:
            close_db_session(session)



class MachineService:
    """Service for machine management"""
    
    @staticmethod
    def get_all_machines():
        """Get all machines"""
        session = get_db_session()
        try:
            machines = session.query(Machine).all()
            return [machine.to_dict() for machine in machines]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_machine_by_id(machine_id):
        """Get machine by ID"""
        session = get_db_session()
        try:
            machine = session.query(Machine).filter(Machine.id == machine_id).first()
            return machine.to_dict() if machine else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_machine_by_code(machine_code):
        """Get machine by machine code"""
        session = get_db_session()
        try:
            machine = session.query(Machine).filter(Machine.machine_code == machine_code).first()
            return machine.to_dict() if machine else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_machine(machine_data):
        """Create a new machine"""
        session = get_db_session()
        try:
            machine = Machine(
                machine_code=machine_data['machine_code'],
                name=machine_data['name'],
                type=machine_data['type'],
                status=machine_data.get('status', 'idle'),
                location=machine_data.get('location')
            )
            session.add(machine)
            session.commit()
            return machine.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_machine(machine_id, machine_data):
        """Update an existing machine"""
        session = get_db_session()
        try:
            machine = session.query(Machine).filter(Machine.id == machine_id).first()
            if not machine:
                return None
            
            # Update fields
            for key, value in machine_data.items():
                if hasattr(machine, key) and key not in ['id', 'created_at', 'updated_at']:
                    setattr(machine, key, value)
            
            session.commit()
            return machine.to_dict()
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_machine(machine_id):
        """Delete a machine"""
        session = get_db_session()
        try:
            machine = session.query(Machine).filter(Machine.id == machine_id).first()
            if not machine:
                return False
            
            session.delete(machine)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def update_machine_status(machine_id, status):
        """Update machine status"""
        session = get_db_session()
        try:
            machine = session.query(Machine).filter(Machine.id == machine_id).first()
            if not machine:
                return None
            
            machine.status = status
            session.commit()
            return machine.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_available_machines():
        """Get all available machines (idle status)"""
        session = get_db_session()
        try:
            machines = session.query(Machine).filter(Machine.status == 'idle').all()
            return [machine.to_dict() for machine in machines]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_machines_by_type(machine_type):
        """Get machines by type"""
        session = get_db_session()
        try:
            machines = session.query(Machine).filter(Machine.type == machine_type).all()
            return [machine.to_dict() for machine in machines]
        finally:
            close_db_session(session)


class SchedulingService:
    """Service for production scheduling"""
    
    @staticmethod
    def get_all_schedule_entries():
        """Get all schedule entries"""
        session = get_db_session()
        try:
            entries = session.query(ProductionSchedule).all()
            return [entry.to_dict() for entry in entries]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_schedule_entry_by_id(entry_id):
        """Get schedule entry by ID"""
        session = get_db_session()
        try:
            entry = session.query(ProductionSchedule).filter(ProductionSchedule.id == entry_id).first()
            return entry.to_dict() if entry else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_schedule_entry(schedule_data):
        """Create a new schedule entry"""
        session = get_db_session()
        try:
            # Validate that machine and work order exist
            machine = session.query(Machine).filter(Machine.id == schedule_data['machine_id']).first()
            work_order = session.query(WorkOrder).filter(WorkOrder.id == schedule_data['work_order_id']).first()
                        # Convert ISO strings to datetime objects
            schedule_data['scheduled_start'] = datetime.datetime.fromisoformat(schedule_data['scheduled_start'])
            schedule_data['scheduled_end'] = datetime.datetime.fromisoformat(schedule_data['scheduled_end'])
            if not machine or not work_order:
                return None
            
            # Create schedule entry
            entry = ProductionSchedule(
                machine_id=schedule_data['machine_id'],
                work_order_id=schedule_data['work_order_id'],
                scheduled_start=schedule_data['scheduled_start'],
                scheduled_end=schedule_data['scheduled_end'],
                priority=schedule_data.get('priority', 1)
            )
            session.add(entry)
            
            # Update work order status to scheduled
            if work_order.status == 'planned':
                work_order.status = 'scheduled'
                work_order.machine_id = machine.id
            
            session.commit()
            return entry.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_schedule_entry(entry_id, schedule_data):
        """Update an existing schedule entry"""
        session = get_db_session()
        try:
            entry = session.query(ProductionSchedule).filter(ProductionSchedule.id == entry_id).first()
            if not entry:
                return None
            
            # Update fields
            for key, value in schedule_data.items():
                if hasattr(entry, key) and key not in ['id', 'created_at', 'updated_at']:
                    setattr(entry, key, value)
            
            session.commit()
            return entry.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_schedule_entry(entry_id):
        """Delete a schedule entry"""
        session = get_db_session()
        try:
            entry = session.query(ProductionSchedule).filter(ProductionSchedule.id == entry_id).first()
            if not entry:
                return False
            
            # Get work order to update its status if needed
            work_order = session.query(WorkOrder).filter(WorkOrder.id == entry.work_order_id).first()
            
            session.delete(entry)
            
            # Check if this was the only schedule entry for the work order
            if work_order and work_order.status == 'scheduled':
                remaining_entries = session.query(ProductionSchedule).filter(
                    ProductionSchedule.work_order_id == work_order.id
                ).count()
                
                if remaining_entries == 0:
                    work_order.status = 'planned'
                    work_order.machine_id = None
            
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_machine_schedule(machine_id, start_date=None, end_date=None):
        """Get schedule for a specific machine"""
        session = get_db_session()
        try:
            query = session.query(ProductionSchedule).filter(ProductionSchedule.machine_id == machine_id)
            
            if start_date:
                query = query.filter(ProductionSchedule.scheduled_end >= start_date)
            
            if end_date:
                query = query.filter(ProductionSchedule.scheduled_start <= end_date)
            
            entries = query.order_by(ProductionSchedule.scheduled_start).all()
            return [entry.to_dict() for entry in entries]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_work_order_schedule(work_order_id):
        """Get schedule entries for a specific work order"""
        session = get_db_session()
        try:
            entries = session.query(ProductionSchedule).filter(
                ProductionSchedule.work_order_id == work_order_id
            ).order_by(ProductionSchedule.scheduled_start).all()
            return [entry.to_dict() for entry in entries]
        finally:
            close_db_session(session)
    
    @staticmethod
    def check_machine_availability(machine_id, start_time, end_time):
        """Check if a machine is available during the specified time period"""
        session = get_db_session()
        try:
            # Check if there are any overlapping schedule entries
            overlapping_entries = session.query(ProductionSchedule).filter(
                ProductionSchedule.machine_id == machine_id,
                ProductionSchedule.scheduled_start < end_time,
                ProductionSchedule.scheduled_end > start_time
            ).all()
            
            if overlapping_entries:
                return {
                    'available': False,
                    'conflicting_entries': [entry.to_dict() for entry in overlapping_entries]
                }
            else:
                return {
                    'available': True
                }
        finally:
            close_db_session(session)
    
    @staticmethod
    def auto_schedule_work_order(work_order_id, estimated_duration_hours=None):
        """Automatically schedule a work order on an available machine"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            if not work_order or work_order.status not in ['planned', 'scheduled']:
                return None
            
            # Get product information to determine machine type
            # In a real system, this would query the ERP for product details
            # For this emulator, we'll assume all products can be produced on any machine
            
            # Find available machines
            available_machines = session.query(Machine).filter(
                Machine.status == 'idle'
            ).all()
            
            if not available_machines:
                return {
                    'success': False,
                    'message': 'No available machines found'
                }
            
            # Use the first available machine
            machine = available_machines[0]
            
            # Determine start and end times
            start_time = datetime.datetime.utcnow()
            
            if not estimated_duration_hours:
                # Estimate duration based on quantity (simplified)
                estimated_duration_hours = work_order.quantity / 10  # Simplified calculation
            
            end_time = start_time + datetime.timedelta(hours=estimated_duration_hours)
            
            # Create schedule entry
            schedule_data = {
                'machine_id': machine.id,
                'work_order_id': work_order.id,
                'scheduled_start': start_time,
                'scheduled_end': end_time,
                'priority': 1
            }
            
            entry = SchedulingService.create_schedule_entry(schedule_data)
            
            return {
                'success': True,
                'schedule_entry': entry
            }
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

class ProductionPlanService:
    """Service for handling production plans in MES"""

    @staticmethod
    def _parse_datetime(value):
        """Convert incoming values (string/date/datetime) to datetime or None"""
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, str):
            try:
                # Allow YYYY-MM-DD by appending midnight
                if len(value) == 10:
                    return datetime.datetime.fromisoformat(value + "T00:00:00")
                return datetime.datetime.fromisoformat(value)
            except ValueError:
                return None
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            return datetime.datetime(value.year, value.month, value.day)
        return None

    @staticmethod
    def get_all_plans():
        session = get_db_session()
        try:
            plans = session.query(ProductionPlan).all()
            return [p.to_dict() for p in plans]
        finally:
            close_db_session(session)

    @staticmethod
    def get_plan_by_id(plan_id):
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.id == plan_id).first()
            return plan.to_dict() if plan else None
        finally:
            close_db_session(session)

    @staticmethod
    def create_plan(data):
        session = get_db_session()
        try:
            plan = ProductionPlan(
                plan_number=data['plan_number'],
                order_id=data.get('order_id'),
                status=data.get('status', 'planned'),
                start_date=ProductionPlanService._parse_datetime(data.get('start_date')),
                end_date=ProductionPlanService._parse_datetime(data.get('end_date')),
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            session.add(plan)
            session.commit()
            return plan.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def update_plan(plan_id, data):
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.id == plan_id).first()
            if not plan:
                return None

            for key, value in data.items():
                if not hasattr(plan, key):
                    continue
                if key in ['start_date', 'end_date']:
                    setattr(plan, key, ProductionPlanService._parse_datetime(value))
                elif key not in ['id', 'created_at']:
                    setattr(plan, key, value)

            plan.updated_at = datetime.datetime.utcnow()
            session.commit()
            return plan.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def delete_plan(plan_id):
        session = get_db_session()
        try:
            plan = session.query(ProductionPlan).filter(ProductionPlan.id == plan_id).first()
            if not plan:
                return False

            session.delete(plan)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
class QualityService:
    """Service for quality control"""
    
    @staticmethod
    def get_all_quality_checks():
        """Get all quality checks"""
        session = get_db_session()
        try:
            checks = session.query(QualityCheck).all()
            return [check.to_dict() for check in checks]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_quality_check_by_id(check_id):
        """Get quality check by ID"""
        session = get_db_session()
        try:
            check = session.query(QualityCheck).filter(QualityCheck.id == check_id).first()
            return check.to_dict() if check else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_quality_check(check_data):
        """Create a new quality check"""
        session = get_db_session()
        try:
            # Determine status based on min/max values if not provided
            if 'status' not in check_data and 'value' in check_data:
                value = check_data['value']
                min_value = check_data.get('min_value')
                max_value = check_data.get('max_value')
                
                if min_value is not None and max_value is not None:
                    if value < min_value or value > max_value:
                        check_data['status'] = 'fail'
                    else:
                        check_data['status'] = 'pass'
                elif min_value is not None and value < min_value:
                    check_data['status'] = 'fail'
                elif max_value is not None and value > max_value:
                    check_data['status'] = 'fail'
                else:
                    check_data['status'] = 'pass'
            
            check = QualityCheck(
                work_order_id=check_data['work_order_id'],
                check_time=check_data.get('check_time', datetime.datetime.utcnow()),
                parameter=check_data['parameter'],
                value=check_data['value'],
                min_value=check_data.get('min_value'),
                max_value=check_data.get('max_value'),
                status=check_data.get('status', 'pass'),
                inspector=check_data.get('inspector'),
                notes=check_data.get('notes')
            )
            session.add(check)
            session.commit()
            return check.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_quality_check(check_id, check_data):
        """Update an existing quality check"""
        session = get_db_session()
        try:
            check = session.query(QualityCheck).filter(QualityCheck.id == check_id).first()
            if not check:
                return None
            
            # Update fields
            for key, value in check_data.items():
                if hasattr(check, key) and key not in ['id']:
                    setattr(check, key, value)
            
            session.commit()
            return check.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_quality_check(check_id):
        """Delete a quality check"""
        session = get_db_session()
        try:
            check = session.query(QualityCheck).filter(QualityCheck.id == check_id).first()
            if not check:
                return False
            
            session.delete(check)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_quality_checks_by_work_order(work_order_id):
        """Get quality checks for a specific work order"""
        session = get_db_session()
        try:
            checks = session.query(QualityCheck).filter(
                QualityCheck.work_order_id == work_order_id
            ).order_by(QualityCheck.check_time).all()
            return [check.to_dict() for check in checks]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_quality_summary_by_work_order(work_order_id):
        """Get quality summary for a specific work order"""
        session = get_db_session()
        try:
            checks = session.query(QualityCheck).filter(
                QualityCheck.work_order_id == work_order_id
            ).all()
            
            total_checks = len(checks)
            pass_checks = sum(1 for check in checks if check.status == 'pass')
            fail_checks = sum(1 for check in checks if check.status == 'fail')
            warning_checks = sum(1 for check in checks if check.status == 'warning')
            
            parameters = {}
            for check in checks:
                if check.parameter not in parameters:
                    parameters[check.parameter] = {
                        'total': 0,
                        'pass': 0,
                        'fail': 0,
                        'warning': 0,
                        'min': None,
                        'max': None,
                        'avg': 0
                    }
                
                param_data = parameters[check.parameter]
                param_data['total'] += 1
                param_data[check.status] += 1
                
                if param_data['min'] is None or check.value < param_data['min']:
                    param_data['min'] = check.value
                
                if param_data['max'] is None or check.value > param_data['max']:
                    param_data['max'] = check.value
                
                param_data['avg'] = (param_data['avg'] * (param_data['total'] - 1) + check.value) / param_data['total']
            
            return {
                'work_order_id': work_order_id,
                'total_checks': total_checks,
                'pass_checks': pass_checks,
                'fail_checks': fail_checks,
                'warning_checks': warning_checks,
                'pass_rate': (pass_checks / total_checks * 100) if total_checks > 0 else 0,
                'parameters': parameters
            }
        finally:
            close_db_session(session)
            
class MaterialByCodeAPI(Resource):
    def get(self, code):
        """Get material by code"""
        try:
            from services import MaterialService  # Make sure it's imported
            materials = MaterialService.get_all_materials()
            for material in materials:
                if material['code'] == code:
                    return material
            return {'error': 'Material not found'}, 404
        except Exception as e:
            return {'error': str(e)}, 500

class MaterialService:
    @staticmethod
    def get_all_materials():
        session = get_db_session()
        try:
            materials = session.query(Material).all()
            return [m.to_dict() for m in materials]
        finally:
            close_db_session(session)


    @staticmethod
    def create_material(data):
        session = get_db_session()
    
        try:
            # Check if material with same code already exists
            existing = session.query(Material).filter_by(code=data['code']).first()
            if existing:
                return existing.to_dict()  # Optionally just return the existing one

            material = Material(
                code=data['code'],
                name=data['name'],
                quantity=data.get('quantity', 0),
                min_quantity=data.get('min_quantity', 0)
            )
            session.add(material)
            session.commit()
            return material.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

    @staticmethod
    def get_material_by_id(material_id):
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            return material.to_dict() if material else None
        finally:
            close_db_session(session)
            
    @staticmethod
    def update_material(material_id, data):
        session = get_db_session()
        try:
            material = session.query(Material).filter(Material.id == material_id).first()
            if not material:
                return None
            if 'code' in data:
                material.code = data['code']
            if 'name' in data:
                material.name = data['name']
            if 'quantity' in data:
                material.quantity = data['quantity']
            if 'min_quantity' in data:
                material.min_quantity = data['min_quantity']

            session.commit()
            return material.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

class MaterialTrackingService:
    """Service for material tracking"""
    
    @staticmethod
    def get_all_material_transactions():
        """Get all material transactions"""
        session = get_db_session()
        try:
            transactions = session.query(MaterialTracking).all()
            return [transaction.to_dict() for transaction in transactions]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_material_transaction_by_id(transaction_id):
        """Get material transaction by ID"""
        session = get_db_session()
        try:
            transaction = session.query(MaterialTracking).filter(MaterialTracking.id == transaction_id).first()
            return transaction.to_dict() if transaction else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_material_transaction(transaction_data):
        """Create a new material transaction"""
        session = get_db_session()
        try:
            transaction = MaterialTracking(
                work_order_id=transaction_data['work_order_id'],
                material_id=transaction_data['material_id'],
                planned_quantity=transaction_data['planned_quantity'],
                actual_quantity=transaction_data.get('actual_quantity'),
                transaction_time=transaction_data.get('transaction_time', datetime.datetime.utcnow()),
                transaction_type=transaction_data['transaction_type']
            )
            session.add(transaction)
            session.commit()
            return transaction.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_material_transaction(transaction_id, transaction_data):
        """Update an existing material transaction"""
        session = get_db_session()
        try:
            transaction = session.query(MaterialTracking).filter(MaterialTracking.id == transaction_id).first()
            if not transaction:
                return None
            
            # Update fields
            for key, value in transaction_data.items():
                if hasattr(transaction, key) and key not in ['id']:
                    setattr(transaction, key, value)
            
            session.commit()
            return transaction.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_material_transaction(transaction_id):
        """Delete a material transaction"""
        session = get_db_session()
        try:
            transaction = session.query(MaterialTracking).filter(MaterialTracking.id == transaction_id).first()
            if not transaction:
                return False
            
            session.delete(transaction)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_material_transactions_by_work_order(work_order_id):
        """Get material transactions for a specific work order"""
        session = get_db_session()
        try:
            transactions = session.query(MaterialTracking).filter(
                MaterialTracking.work_order_id == work_order_id
            ).order_by(MaterialTracking.transaction_time).all()
            return [transaction.to_dict() for transaction in transactions]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_material_transactions_by_material(material_id):
        """Get material transactions for a specific material"""
        session = get_db_session()
        try:
            transactions = session.query(MaterialTracking).filter(
                MaterialTracking.material_id == material_id
            ).order_by(MaterialTracking.transaction_time).all()
            return [transaction.to_dict() for transaction in transactions]
        finally:
            close_db_session(session)
    
    @staticmethod
    def allocate_materials_for_work_order(work_order_id, erp_api_url):
        """Allocate materials for a work order based on BOM"""
        session = get_db_session()
        try:
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            if not work_order:
                return None
            
            # Get product BOM from ERP
            response = requests.get(f"{erp_api_url}/products/{work_order.product_id}/bom")
            if response.status_code != 200:
                return None
            
            bom_items = response.json()
            
            # Create material allocation transactions
            transactions = []
            for bom_item in bom_items:
                material_id = bom_item['material_id']
                quantity = bom_item['quantity'] * work_order.quantity
                
                transaction_data = {
                    'work_order_id': work_order_id,
                    'material_id': material_id,
                    'planned_quantity': quantity,
                    'transaction_type': 'allocation'
                }
                
                transaction = MaterialTrackingService.create_material_transaction(transaction_data)
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def consume_materials_for_work_order(work_order_id, erp_api_url):
        """Consume materials for a work order and update ERP inventory"""
        session = get_db_session()
        try:
            # Skip if already consumed
            existing_consumption = session.query(MaterialTracking).filter(
                MaterialTracking.work_order_id == work_order_id,
                MaterialTracking.transaction_type == 'consumption'
            ).first()
            if existing_consumption:
                return []

            # Get material allocations
            allocations = session.query(MaterialTracking).filter(
                MaterialTracking.work_order_id == work_order_id,
                MaterialTracking.transaction_type == 'allocation'
            ).all()

            # If no allocations exist yet, create them from BOM now
            if not allocations:
                allocs = MaterialTrackingService.allocate_materials_for_work_order(work_order_id, erp_api_url)
                # reload from DB to ensure ids are present
                allocations = session.query(MaterialTracking).filter(
                    MaterialTracking.work_order_id == work_order_id,
                    MaterialTracking.transaction_type == 'allocation'
                ).all()

            if not allocations:
                return None
            
            # Create consumption transactions and update ERP inventory
            consumption_transactions = []
            for allocation in allocations:
                # Create consumption transaction
                transaction_data = {
                    'work_order_id': work_order_id,
                    'material_id': allocation.material_id,
                    'planned_quantity': allocation.planned_quantity,
                    'actual_quantity': allocation.planned_quantity,  # Simplified: assume actual = planned
                    'transaction_type': 'consumption'
                }
                
                transaction = MaterialTrackingService.create_material_transaction(transaction_data)
                consumption_transactions.append(transaction)
                
                # Update ERP inventory (negative quantity for consumption)
                try:
                    requests.put(
                        f"{erp_api_url}/materials/{allocation.material_id}/stock",
                        json={
                            'quantity_change': -allocation.planned_quantity,
                            'transaction_type': 'production_consumption'
                        }
                    )
                except Exception as e:
                    # Log error but continue with other materials
                    print(f"Error updating ERP inventory: {str(e)}")
            
            return consumption_transactions
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)



class ProductionCountService:
    """Service for production count tracking"""
    
    @staticmethod
    def get_all_production_counts():
        """Get all production counts"""
        session = get_db_session()
        try:
            counts = session.query(ProductionCount).all()
            return [count.to_dict() for count in counts]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_production_count_by_id(count_id):
        """Get production count by ID"""
        session = get_db_session()
        try:
            count = session.query(ProductionCount).filter(ProductionCount.id == count_id).first()
            return count.to_dict() if count else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_production_count(count_data):
        """Create a new production count"""
        session = get_db_session()
        try:
            count = ProductionCount(
                work_order_id=count_data['work_order_id'],
                count_time=count_data.get('count_time', datetime.datetime.utcnow()),
                good_count=count_data.get('good_count', 0),
                reject_count=count_data.get('reject_count', 0),
                rework_count=count_data.get('rework_count', 0)
            )
            session.add(count)
            session.commit()
            return count.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_production_count(count_id, count_data):
        """Update an existing production count"""
        session = get_db_session()
        try:
            count = session.query(ProductionCount).filter(ProductionCount.id == count_id).first()
            if not count:
                return None
            
            # Update fields
            for key, value in count_data.items():
                if hasattr(count, key) and key not in ['id']:
                    setattr(count, key, value)
            
            session.commit()
            return count.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_production_count(count_id):
        """Delete a production count"""
        session = get_db_session()
        try:
            count = session.query(ProductionCount).filter(ProductionCount.id == count_id).first()
            if not count:
                return False
            
            session.delete(count)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_production_counts_by_work_order(work_order_id):
        """Get production counts for a specific work order"""
        session = get_db_session()
        try:
            counts = session.query(ProductionCount).filter(
                ProductionCount.work_order_id == work_order_id
            ).order_by(ProductionCount.count_time).all()
            return [count.to_dict() for count in counts]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_production_summary_by_work_order(work_order_id):
        """Get production summary for a specific work order"""
        session = get_db_session()
        try:
            counts = session.query(ProductionCount).filter(
                ProductionCount.work_order_id == work_order_id
            ).all()
            
            total_good = sum(count.good_count for count in counts)
            total_reject = sum(count.reject_count for count in counts)
            total_rework = sum(count.rework_count for count in counts)
            total_count = total_good + total_reject + total_rework
            
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            target_quantity = work_order.quantity if work_order else 0
            
            return {
                'work_order_id': work_order_id,
                'work_order_number': work_order.work_order_number if work_order else None,
                'target_quantity': target_quantity,
                'total_good': total_good,
                'total_reject': total_reject,
                'total_rework': total_rework,
                'total_count': total_count,
                'completion_percentage': (total_good / target_quantity * 100) if target_quantity > 0 else 0,
                'yield_percentage': (total_good / total_count * 100) if total_count > 0 else 0
            }
        finally:
            close_db_session(session)
    
    @staticmethod
    def increment_production_count(work_order_id, good=0, reject=0, rework=0):
        """Increment production count for a work order"""
        session = get_db_session()
        try:
            # Create a new count record
            count_data = {
                'work_order_id': work_order_id,
                'good_count': good,
                'reject_count': reject,
                'rework_count': rework
            }
            
            count = ProductionCountService.create_production_count(count_data)
            
            # Check if work order is complete
            summary = ProductionCountService.get_production_summary_by_work_order(work_order_id)
            work_order = session.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
            
            if work_order and summary['total_good'] >= work_order.quantity:
                work_order.status = 'completed'
                work_order.end_time = datetime.datetime.utcnow()
                session.commit()
            
            return count
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)


class DowntimeService:
    """Service for downtime tracking"""
    
    @staticmethod
    def get_all_downtimes():
        """Get all downtimes"""
        session = get_db_session()
        try:
            downtimes = session.query(Downtime).all()
            return [downtime.to_dict() for downtime in downtimes]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_downtime_by_id(downtime_id):
        """Get downtime by ID"""
        session = get_db_session()
        try:
            downtime = session.query(Downtime).filter(Downtime.id == downtime_id).first()
            return downtime.to_dict() if downtime else None
        finally:
            close_db_session(session)
    
    @staticmethod
    def create_downtime(downtime_data):
        """Create a new downtime"""
        session = get_db_session()
        try:
            downtime = Downtime(
                machine_id=downtime_data['machine_id'],
                work_order_id=downtime_data.get('work_order_id'),
                start_time=downtime_data.get('start_time', datetime.datetime.utcnow()),
                end_time=downtime_data.get('end_time'),
                reason=downtime_data['reason'],
                category=downtime_data['category'],
                notes=downtime_data.get('notes')
            )
            session.add(downtime)
            
            # Update machine status if downtime is starting now
            if not downtime_data.get('end_time'):
                machine = session.query(Machine).filter(Machine.id == downtime_data['machine_id']).first()
                if machine:
                    if downtime_data['category'] == 'planned':
                        machine.status = 'maintenance'
                    else:
                        machine.status = 'error'
            
            session.commit()
            return downtime.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def update_downtime(downtime_id, downtime_data):
        """Update an existing downtime"""
        session = get_db_session()
        try:
            downtime = session.query(Downtime).filter(Downtime.id == downtime_id).first()
            if not downtime:
                return None
            
            # Check if we're ending the downtime
            ending_downtime = 'end_time' in downtime_data and downtime_data['end_time'] and not downtime.end_time
            
            # Update fields
            for key, value in downtime_data.items():
                if hasattr(downtime, key) and key not in ['id']:
                    setattr(downtime, key, value)
            
            # If ending downtime, update machine status
            if ending_downtime:
                machine = session.query(Machine).filter(Machine.id == downtime.machine_id).first()
                if machine:
                    # Check if there's an active work order for this machine
                    active_work_order = session.query(WorkOrder).filter(
                        WorkOrder.machine_id == machine.id,
                        WorkOrder.status == 'in_progress'
                    ).first()
                    
                    if active_work_order:
                        machine.status = 'running'
                    else:
                        machine.status = 'idle'
            
            session.commit()
            return downtime.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def delete_downtime(downtime_id):
        """Delete a downtime"""
        session = get_db_session()
        try:
            downtime = session.query(Downtime).filter(Downtime.id == downtime_id).first()
            if not downtime:
                return False
            
            session.delete(downtime)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_downtimes_by_machine(machine_id, start_date=None, end_date=None):
        """Get downtimes for a specific machine"""
        session = get_db_session()
        try:
            query = session.query(Downtime).filter(Downtime.machine_id == machine_id)
            
            if start_date:
                query = query.filter(Downtime.start_time >= start_date)
            
            if end_date:
                query = query.filter(Downtime.start_time <= end_date)
            
            downtimes = query.order_by(Downtime.start_time).all()
            return [downtime.to_dict() for downtime in downtimes]
        finally:
            close_db_session(session)
    
    @staticmethod
    def get_active_downtimes():
        """Get all active downtimes (no end time)"""
        session = get_db_session()
        try:
            downtimes = session.query(Downtime).filter(Downtime.end_time == None).all()
            return [downtime.to_dict() for downtime in downtimes]
        finally:
            close_db_session(session)
    
    @staticmethod
    def end_downtime(downtime_id):
        """End a downtime event"""
        session = get_db_session()
        try:
            downtime = session.query(Downtime).filter(Downtime.id == downtime_id).first()
            if not downtime or downtime.end_time:
                return None
            
            downtime.end_time = datetime.datetime.utcnow()
            
            # Update machine status
            machine = session.query(Machine).filter(Machine.id == downtime.machine_id).first()
            if machine:
                # Check if there's an active work order for this machine
                active_work_order = session.query(WorkOrder).filter(
                    WorkOrder.machine_id == machine.id,
                    WorkOrder.status == 'in_progress'
                ).first()
                
                if active_work_order:
                    machine.status = 'running'
                else:
                    machine.status = 'idle'
            
            session.commit()
            return downtime.to_dict()
        except SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            close_db_session(session)

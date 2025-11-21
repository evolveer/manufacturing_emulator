"""
MES Emulator - Data Models
Defines SQLAlchemy ORM models for the MES database
"""
import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class WorkOrder(Base):
    """Work order model representing production tasks"""
    __tablename__ = 'work_orders'
    
    id = Column(Integer, primary_key=True)
    work_order_number = Column(String, unique=True, nullable=False)
    production_plan_id = Column(Integer, ForeignKey('production_plans.id'), nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # 'planned', 'scheduled', 'in_progress', 'completed', 'cancelled'
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    machine_id = Column(Integer, ForeignKey('machines.id'))
    inventory_posted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    machine = relationship("Machine", back_populates="work_orders")
    schedule_entries = relationship("ProductionSchedule", back_populates="work_order")
    quality_checks = relationship("QualityCheck", back_populates="work_order")
    
    def __repr__(self):
        return f"<WorkOrder(number='{self.work_order_number}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'work_order_number': self.work_order_number,
            'production_plan_id': self.production_plan_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'machine_id': self.machine_id,
            'machine_code': self.machine.machine_code if self.machine else None,
            'inventory_posted': self.inventory_posted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Machine(Base):
    """Machine model representing production equipment"""
    __tablename__ = 'machines'
    
    id = Column(Integer, primary_key=True)
    machine_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # 'idle', 'setup', 'running', 'maintenance', 'error'
    location = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    work_orders = relationship("WorkOrder", back_populates="machine")
    schedule_entries = relationship("ProductionSchedule", back_populates="machine")
    
    def __repr__(self):
        return f"<Machine(code='{self.machine_code}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_code': self.machine_code,
            'name': self.name,
            'type': self.type,
            'status': self.status,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProductionSchedule(Base):
    """Production schedule model representing planned machine assignments"""
    __tablename__ = 'production_schedule'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    machine = relationship("Machine", back_populates="schedule_entries")
    work_order = relationship("WorkOrder", back_populates="schedule_entries")
    
    def __repr__(self):
        return f"<ProductionSchedule(machine_id={self.machine_id}, work_order_id={self.work_order_id})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'machine_code': self.machine.machine_code if self.machine else None,
            'work_order_id': self.work_order_id,
            'work_order_number': self.work_order.work_order_number if self.work_order else None,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'scheduled_end': self.scheduled_end.isoformat() if self.scheduled_end else None,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class QualityCheck(Base):
    """Quality check model representing quality control measurements"""
    __tablename__ = 'quality_checks'
    
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    check_time = Column(DateTime, default=datetime.datetime.utcnow)
    parameter = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    min_value = Column(Float)
    max_value = Column(Float)
    status = Column(String, nullable=False)  # 'pass', 'fail', 'warning'
    inspector = Column(String)
    notes = Column(Text)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="quality_checks")
    
    def __repr__(self):
        return f"<QualityCheck(parameter='{self.parameter}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'work_order_id': self.work_order_id,
            'work_order_number': self.work_order.work_order_number if self.work_order else None,
            'check_time': self.check_time.isoformat() if self.check_time else None,
            'parameter': self.parameter,
            'value': self.value,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'status': self.status,
            'inspector': self.inspector,
            'notes': self.notes
        }


class MaterialTracking(Base):
    """Material tracking model for tracking material consumption in production"""
    __tablename__ = 'material_tracking'
    
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    material_id = Column(Integer, nullable=False)
    planned_quantity = Column(Float, nullable=False)
    actual_quantity = Column(Float)
    transaction_time = Column(DateTime, default=datetime.datetime.utcnow)
    transaction_type = Column(String, nullable=False)  # 'allocation', 'consumption', 'return'
    
    # Relationships
    work_order = relationship("WorkOrder")
    
    def __repr__(self):
        return f"<MaterialTracking(material_id={self.material_id}, transaction_type='{self.transaction_type}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'work_order_id': self.work_order_id,
            'work_order_number': self.work_order.work_order_number if self.work_order else None,
            'material_id': self.material_id,
            'planned_quantity': self.planned_quantity,
            'actual_quantity': self.actual_quantity,
            'transaction_time': self.transaction_time.isoformat() if self.transaction_time else None,
            'transaction_type': self.transaction_type
        }
class ProductionPlan(Base):
    __tablename__ = 'production_plans'

    id = Column(Integer, primary_key=True)
    plan_number = Column(String, unique=True, nullable=False)
    order_id = Column(Integer, nullable=True)  # Could be ForeignKey to an ERP order table
    status = Column(String, default='planned')
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    work_orders = relationship("WorkOrder", backref="production_plan")

    def to_dict(self):
        return {
            'id': self.id,
            'plan_number': self.plan_number,
            'order_id': self.order_id,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProductionCount(Base):
    """Production count model for tracking production quantities"""
    __tablename__ = 'production_counts'
    
    id = Column(Integer, primary_key=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    count_time = Column(DateTime, default=datetime.datetime.utcnow)
    good_count = Column(Integer, default=0)
    reject_count = Column(Integer, default=0)
    rework_count = Column(Integer, default=0)
    
    # Relationships
    work_order = relationship("WorkOrder")
    
    def __repr__(self):
        return f"<ProductionCount(work_order_id={self.work_order_id}, good_count={self.good_count})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'work_order_id': self.work_order_id,
            'work_order_number': self.work_order.work_order_number if self.work_order else None,
            'count_time': self.count_time.isoformat() if self.count_time else None,
            'good_count': self.good_count,
            'reject_count': self.reject_count,
            'rework_count': self.rework_count,
            'total_count': self.good_count + self.reject_count + self.rework_count
        }


class Downtime(Base):
    """Downtime model for tracking machine downtime events"""
    __tablename__ = 'downtimes'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    reason = Column(String, nullable=False)
    category = Column(String, nullable=False)  # 'planned', 'unplanned'
    notes = Column(Text)
    
    # Relationships
    machine = relationship("Machine")
    work_order = relationship("WorkOrder")
    
    def __repr__(self):
        return f"<Downtime(machine_id={self.machine_id}, reason='{self.reason}')>"
    
    def to_dict(self):
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds() / 60  # Duration in minutes
        
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'machine_code': self.machine.machine_code if self.machine else None,
            'work_order_id': self.work_order_id,
            'work_order_number': self.work_order.work_order_number if self.work_order else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': duration,
            'reason': self.reason,
            'category': self.category,
            'notes': self.notes
        }
        
class Material(Base):
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    min_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'quantity': self.quantity,
            'min_quantity': self.min_quantity
        }
       

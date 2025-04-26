"""
PCS Emulator - Data Models
Defines SQLAlchemy ORM models for the PCS database
"""
import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class MachineParameter(Base):
    """Machine parameter model representing control parameters for machines"""
    __tablename__ = 'machine_parameters'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    parameter_name = Column(String, nullable=False)
    current_value = Column(Float)
    set_point = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    unit = Column(String)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('machine_id', 'parameter_name', name='_machine_parameter_uc'),)
    
    def __repr__(self):
        return f"<MachineParameter(machine_id={self.machine_id}, name='{self.parameter_name}', value={self.current_value})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'parameter_name': self.parameter_name,
            'current_value': self.current_value,
            'set_point': self.set_point,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'unit': self.unit,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SensorData(Base):
    """Sensor data model representing measurements from machine sensors"""
    __tablename__ = 'sensor_data'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    sensor_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    quality = Column(Integer, default=100)  # Data quality indicator (0-100)
    
    def __repr__(self):
        return f"<SensorData(machine_id={self.machine_id}, sensor='{self.sensor_name}', value={self.value})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'sensor_name': self.sensor_name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'quality': self.quality
        }


class Alarm(Base):
    """Alarm model representing machine alarms and warnings"""
    __tablename__ = 'alarms'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    alarm_code = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String, nullable=False)  # 'info', 'warning', 'error', 'critical'
    status = Column(String, nullable=False)  # 'active', 'acknowledged', 'resolved'
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    acknowledged = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Alarm(machine_id={self.machine_id}, code='{self.alarm_code}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'alarm_code': self.alarm_code,
            'description': self.description,
            'severity': self.severity,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'acknowledged': self.acknowledged
        }


class MachineState(Base):
    """Machine state model representing the operational state of machines"""
    __tablename__ = 'machine_states'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    state = Column(String, nullable=False)  # 'idle', 'setup', 'running', 'error', 'maintenance', 'shutdown'
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    work_order_id = Column(Integer)
    cycle_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<MachineState(machine_id={self.machine_id}, state='{self.state}')>"
    
    def to_dict(self):
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'state': self.state,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': duration,
            'work_order_id': self.work_order_id,
            'cycle_count': self.cycle_count
        }


class CycleData(Base):
    """Cycle data model representing individual production cycles"""
    __tablename__ = 'cycle_data'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    work_order_id = Column(Integer)
    cycle_number = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    cycle_time = Column(Float)  # Duration in seconds
    status = Column(String)  # 'completed', 'aborted', 'error'
    
    def __repr__(self):
        return f"<CycleData(machine_id={self.machine_id}, cycle_number={self.cycle_number})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'work_order_id': self.work_order_id,
            'cycle_number': self.cycle_number,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'cycle_time': self.cycle_time,
            'status': self.status
        }


class MachineCommand(Base):
    """Machine command model representing commands sent to machines"""
    __tablename__ = 'machine_commands'
    
    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, nullable=False)
    command_type = Column(String, nullable=False)  # 'start', 'stop', 'reset', 'parameter_change', etc.
    parameters = Column(Text)  # JSON string of command parameters
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, nullable=False)  # 'pending', 'executed', 'failed'
    response = Column(Text)
    
    def __repr__(self):
        return f"<MachineCommand(machine_id={self.machine_id}, type='{self.command_type}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'command_type': self.command_type,
            'parameters': self.parameters,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'status': self.status,
            'response': self.response
        }

class WorkOrder(Base):
    __tablename__ = 'work_orders'
    
    id = Column(Integer, primary_key=True)
    work_order_number = Column(String(255), unique=True, nullable=False)
    production_plan_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    machine_id = Column(Integer, ForeignKey('machines.id'))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

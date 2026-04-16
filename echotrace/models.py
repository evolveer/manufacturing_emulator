"""
EchoTrace Data Models
Audit trail models compliant with FDA 21 CFR Part 11 (ALCOA+ principles)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditTrail(Base):
    """
    Comprehensive audit trail model capturing all system changes
    Implements ALCOA+ principles:
    - Attributable: user_id, username
    - Legible: clear action descriptions
    - Contemporaneous: timestamp at time of action
    - Original: immutable records
    - Accurate: validated data
    - Complete: all required fields
    - Consistent: standardized format
    - Enduring: permanent storage
    - Available: searchable and reportable
    """
    __tablename__ = 'audit_trail'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Who: User identification (Attributable)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100), nullable=False, index=True)
    user_role = Column(String(50), nullable=True)
    
    # What: Action details (Legible, Complete)
    action = Column(String(50), nullable=False, index=True)  # CREATE, READ, UPDATE, DELETE, APPROVE, REJECT, etc.
    entity_type = Column(String(50), nullable=False, index=True)  # Order, Material, Batch, Equipment, etc.
    entity_id = Column(String(100), nullable=False, index=True)  # ID of the affected entity
    entity_name = Column(String(200), nullable=True)  # Human-readable name
    
    # When: Timestamp (Contemporaneous)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Why: Reason for change (Required for certain actions)
    reason = Column(Text, nullable=True)
    
    # Details: Before and after values (Accurate, Complete)
    old_value = Column(JSON, nullable=True)  # Previous state
    new_value = Column(JSON, nullable=True)  # New state
    changes = Column(JSON, nullable=True)  # Specific fields changed
    
    # Context: Additional information
    source_system = Column(String(50), nullable=False, index=True)  # ERP, MES, PCS, EchoTrace
    source_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    session_id = Column(String(100), nullable=True, index=True)
    
    # Traceability: Related records
    parent_id = Column(Integer, nullable=True, index=True)  # Link to parent audit record
    batch_number = Column(String(100), nullable=True, index=True)  # For manufacturing traceability
    order_number = Column(String(100), nullable=True, index=True)  # For order traceability
    
    # Compliance: Signature and verification
    signature = Column(String(500), nullable=True)  # Electronic signature hash
    signature_meaning = Column(String(200), nullable=True)  # What the signature represents
    
    # Integrity: Tamper detection
    record_hash = Column(String(64), nullable=False)  # SHA-256 hash of record
    previous_hash = Column(String(64), nullable=True)  # Hash of previous record (blockchain-style)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_entity_timestamp', 'entity_type', 'entity_id', 'timestamp'),
        Index('idx_action_timestamp', 'action', 'timestamp'),
        Index('idx_batch_timestamp', 'batch_number', 'timestamp'),
        Index('idx_order_timestamp', 'order_number', 'timestamp'),
        Index('idx_source_timestamp', 'source_system', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditTrail(id={self.id}, user={self.username}, action={self.action}, entity={self.entity_type}:{self.entity_id}, timestamp={self.timestamp})>"
    
    def to_dict(self):
        """Convert audit trail record to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'user_role': self.user_role,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'entity_name': self.entity_name,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'reason': self.reason,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'changes': self.changes,
            'source_system': self.source_system,
            'source_ip': self.source_ip,
            'session_id': self.session_id,
            'parent_id': self.parent_id,
            'batch_number': self.batch_number,
            'order_number': self.order_number,
            'signature': self.signature,
            'signature_meaning': self.signature_meaning,
            'record_hash': self.record_hash,
            'previous_hash': self.previous_hash,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AuditTrailArchive(Base):
    """
    Archive table for old audit trail records (7-year retention)
    Same structure as AuditTrail but for long-term storage
    """
    __tablename__ = 'audit_trail_archive'
    
    # Same columns as AuditTrail
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String(100), nullable=False)
    user_role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    entity_name = Column(String(200), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changes = Column(JSON, nullable=True)
    source_system = Column(String(50), nullable=False)
    source_ip = Column(String(45), nullable=True)
    session_id = Column(String(100), nullable=True)
    parent_id = Column(Integer, nullable=True)
    batch_number = Column(String(100), nullable=True)
    order_number = Column(String(100), nullable=True)
    signature = Column(String(500), nullable=True)
    signature_meaning = Column(String(200), nullable=True)
    record_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False)
    archived_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<AuditTrailArchive(id={self.id}, archived_at={self.archived_at})>"

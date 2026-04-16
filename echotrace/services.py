"""
EchoTrace Services
Core audit trail logging and retrieval services
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session

from echotrace.models import AuditTrail, AuditTrailArchive
from echotrace.database import get_db_session


class AuditTrailService:
    """Service for creating and managing audit trail records"""
    
    @staticmethod
    def _calculate_hash(record_data: Dict[str, Any]) -> str:
        """
        Calculate SHA-256 hash of audit record for integrity verification
        """
        # Create a deterministic string representation
        hash_string = json.dumps(record_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    @staticmethod
    def _get_previous_hash(session: Session) -> Optional[str]:
        """
        Get the hash of the most recent audit record (blockchain-style chaining)
        """
        last_record = session.query(AuditTrail).order_by(desc(AuditTrail.id)).first()
        return last_record.record_hash if last_record else None
    
    @staticmethod
    def log_action(
        user_id: int,
        username: str,
        action: str,
        entity_type: str,
        entity_id: str,
        source_system: str,
        user_role: Optional[str] = None,
        entity_name: Optional[str] = None,
        reason: Optional[str] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        changes: Optional[Dict] = None,
        source_ip: Optional[str] = None,
        session_id: Optional[str] = None,
        parent_id: Optional[int] = None,
        batch_number: Optional[str] = None,
        order_number: Optional[str] = None,
        signature: Optional[str] = None,
        signature_meaning: Optional[str] = None
    ) -> AuditTrail:
        """
        Log an audit trail entry
        
        Args:
            user_id: ID of the user performing the action
            username: Username of the user
            action: Action performed (CREATE, READ, UPDATE, DELETE, APPROVE, REJECT, etc.)
            entity_type: Type of entity affected (Order, Material, Batch, Equipment, etc.)
            entity_id: ID of the affected entity
            source_system: System where action originated (ERP, MES, PCS, EchoTrace)
            user_role: Role of the user (optional)
            entity_name: Human-readable name of entity (optional)
            reason: Reason for the action (optional, required for certain actions)
            old_value: Previous state of the entity (optional)
            new_value: New state of the entity (optional)
            changes: Specific fields that changed (optional)
            source_ip: IP address of the user (optional)
            session_id: Session ID (optional)
            parent_id: ID of parent audit record for linking (optional)
            batch_number: Batch number for traceability (optional)
            order_number: Order number for traceability (optional)
            signature: Electronic signature hash (optional)
            signature_meaning: What the signature represents (optional)
        
        Returns:
            AuditTrail: The created audit trail record
        """
        with get_db_session() as session:
            # Get previous hash for blockchain-style chaining
            previous_hash = AuditTrailService._get_previous_hash(session)
            
            # Prepare record data for hashing
            record_data = {
                'user_id': user_id,
                'username': username,
                'action': action,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'timestamp': datetime.utcnow().isoformat(),
                'reason': reason,
                'old_value': old_value,
                'new_value': new_value,
                'source_system': source_system,
                'previous_hash': previous_hash
            }
            
            # Calculate hash for integrity
            record_hash = AuditTrailService._calculate_hash(record_data)
            
            # Create audit trail record
            audit_record = AuditTrail(
                user_id=user_id,
                username=username,
                user_role=user_role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                timestamp=datetime.utcnow(),
                reason=reason,
                old_value=old_value,
                new_value=new_value,
                changes=changes,
                source_system=source_system,
                source_ip=source_ip,
                session_id=session_id,
                parent_id=parent_id,
                batch_number=batch_number,
                order_number=order_number,
                signature=signature,
                signature_meaning=signature_meaning,
                record_hash=record_hash,
                previous_hash=previous_hash
            )
            
            session.add(audit_record)
            session.commit()
            session.refresh(audit_record)
            
            return audit_record
    
    @staticmethod
    def verify_integrity(audit_id: int) -> Dict[str, Any]:
        """
        Verify the integrity of an audit record by recalculating its hash
        
        Args:
            audit_id: ID of the audit record to verify
        
        Returns:
            Dict with verification results
        """
        with get_db_session() as session:
            record = session.query(AuditTrail).filter(AuditTrail.id == audit_id).first()
            
            if not record:
                return {'valid': False, 'error': 'Record not found'}
            
            # Recalculate hash
            record_data = {
                'user_id': record.user_id,
                'username': record.username,
                'action': record.action,
                'entity_type': record.entity_type,
                'entity_id': record.entity_id,
                'timestamp': record.timestamp.isoformat(),
                'reason': record.reason,
                'old_value': record.old_value,
                'new_value': record.new_value,
                'source_system': record.source_system,
                'previous_hash': record.previous_hash
            }
            
            calculated_hash = AuditTrailService._calculate_hash(record_data)
            
            # Verify chain integrity
            if record.previous_hash:
                previous_record = session.query(AuditTrail).filter(
                    AuditTrail.id == record.id - 1
                ).first()
                
                chain_valid = (
                    previous_record and 
                    previous_record.record_hash == record.previous_hash
                )
            else:
                chain_valid = True  # First record
            
            return {
                'valid': calculated_hash == record.record_hash and chain_valid,
                'stored_hash': record.record_hash,
                'calculated_hash': calculated_hash,
                'chain_valid': chain_valid,
                'record_id': audit_id
            }


class AuditTrailSearchService:
    """Service for searching and filtering audit trail records"""
    
    @staticmethod
    def search(
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        source_system: Optional[str] = None,
        batch_number: Optional[str] = None,
        order_number: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'timestamp',
        order_direction: str = 'desc'
    ) -> Dict[str, Any]:
        """
        Advanced search for audit trail records
        
        Args:
            user_id: Filter by user ID
            username: Filter by username (partial match)
            action: Filter by action type
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            source_system: Filter by source system
            batch_number: Filter by batch number
            order_number: Filter by order number
            start_date: Filter by start date
            end_date: Filter by end date
            search_text: Full-text search across multiple fields
            limit: Maximum number of records to return
            offset: Number of records to skip (for pagination)
            order_by: Field to order by
            order_direction: Order direction ('asc' or 'desc')
        
        Returns:
            Dict with search results and metadata
        """
        with get_db_session() as session:
            # Build query
            query = session.query(AuditTrail)
            
            # Apply filters
            filters = []
            
            if user_id is not None:
                filters.append(AuditTrail.user_id == user_id)
            
            if username:
                filters.append(AuditTrail.username.like(f'%{username}%'))
            
            if action:
                filters.append(AuditTrail.action == action)
            
            if entity_type:
                filters.append(AuditTrail.entity_type == entity_type)
            
            if entity_id:
                filters.append(AuditTrail.entity_id == entity_id)
            
            if source_system:
                filters.append(AuditTrail.source_system == source_system)
            
            if batch_number:
                filters.append(AuditTrail.batch_number == batch_number)
            
            if order_number:
                filters.append(AuditTrail.order_number == order_number)
            
            if start_date:
                filters.append(AuditTrail.timestamp >= start_date)
            
            if end_date:
                filters.append(AuditTrail.timestamp <= end_date)
            
            if search_text:
                # Full-text search across multiple fields
                search_filters = [
                    AuditTrail.username.like(f'%{search_text}%'),
                    AuditTrail.entity_name.like(f'%{search_text}%'),
                    AuditTrail.reason.like(f'%{search_text}%'),
                    AuditTrail.entity_id.like(f'%{search_text}%'),
                ]
                filters.append(or_(*search_filters))
            
            # Apply all filters
            if filters:
                query = query.filter(and_(*filters))
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply ordering
            order_column = getattr(AuditTrail, order_by, AuditTrail.timestamp)
            if order_direction.lower() == 'desc':
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(order_column)
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute query
            records = query.all()
            
            return {
                'records': [record.to_dict() for record in records],
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'returned_count': len(records)
            }
    
    @staticmethod
    def get_entity_history(
        entity_type: str,
        entity_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get complete history of changes for a specific entity
        
        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            limit: Maximum number of records
        
        Returns:
            List of audit trail records for the entity
        """
        with get_db_session() as session:
            records = session.query(AuditTrail).filter(
                and_(
                    AuditTrail.entity_type == entity_type,
                    AuditTrail.entity_id == entity_id
                )
            ).order_by(desc(AuditTrail.timestamp)).limit(limit).all()
            
            return [record.to_dict() for record in records]
    
    @staticmethod
    def get_user_activity(
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all activity for a specific user
        
        Args:
            user_id: ID of user
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum number of records
        
        Returns:
            List of audit trail records for the user
        """
        with get_db_session() as session:
            query = session.query(AuditTrail).filter(AuditTrail.user_id == user_id)
            
            if start_date:
                query = query.filter(AuditTrail.timestamp >= start_date)
            
            if end_date:
                query = query.filter(AuditTrail.timestamp <= end_date)
            
            records = query.order_by(desc(AuditTrail.timestamp)).limit(limit).all()
            
            return [record.to_dict() for record in records]
    
    @staticmethod
    def get_statistics(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit trail statistics
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
        
        Returns:
            Dict with statistics
        """
        with get_db_session() as session:
            query = session.query(AuditTrail)
            
            if start_date:
                query = query.filter(AuditTrail.timestamp >= start_date)
            
            if end_date:
                query = query.filter(AuditTrail.timestamp <= end_date)
            
            # Total records
            total_records = query.count()
            
            # Records by action
            by_action = session.query(
                AuditTrail.action,
                func.count(AuditTrail.id).label('count')
            ).group_by(AuditTrail.action).all()
            
            # Records by entity type
            by_entity = session.query(
                AuditTrail.entity_type,
                func.count(AuditTrail.id).label('count')
            ).group_by(AuditTrail.entity_type).all()
            
            # Records by system
            by_system = session.query(
                AuditTrail.source_system,
                func.count(AuditTrail.id).label('count')
            ).group_by(AuditTrail.source_system).all()
            
            # Top users
            top_users = session.query(
                AuditTrail.username,
                func.count(AuditTrail.id).label('count')
            ).group_by(AuditTrail.username).order_by(desc('count')).limit(10).all()
            
            return {
                'total_records': total_records,
                'by_action': {action: count for action, count in by_action},
                'by_entity_type': {entity: count for entity, count in by_entity},
                'by_source_system': {system: count for system, count in by_system},
                'top_users': [{'username': user, 'count': count} for user, count in top_users]
            }

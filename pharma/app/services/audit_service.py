"""
Audit Service
Records and retrieves audit trail events for all critical actions.
"""

from __future__ import annotations

from typing import List, Optional

from ..domain.models import AuditEvent
from ..utils.persistence import load_all, upsert


ENTITY = "audit_events"


def log_event(
    user: str,
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    comment: Optional[str] = None,
) -> AuditEvent:
    """Create and persist a new audit event."""
    event = AuditEvent(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        comment=comment,
    )
    upsert(ENTITY, AuditEvent, event, "event_id")
    return event


def get_all_events() -> List[AuditEvent]:
    return load_all(ENTITY, AuditEvent)


def get_events_for_batch(batch_id: str) -> List[AuditEvent]:
    return [e for e in get_all_events() if e.entity_id == batch_id or e.comment and batch_id in e.comment]


def get_events_filtered(
    batch_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    user: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[AuditEvent]:
    events = get_all_events()
    if batch_id:
        events = [e for e in events if batch_id in (e.entity_id or "") or batch_id in (e.comment or "")]
    if entity_type:
        events = [e for e in events if e.entity_type == entity_type]
    if user:
        events = [e for e in events if user.lower() in e.user.lower()]
    if action:
        events = [e for e in events if action.lower() in e.action.lower()]
    if date_from:
        events = [e for e in events if e.timestamp >= date_from]
    if date_to:
        events = [e for e in events if e.timestamp <= date_to + "T23:59:59"]
    return sorted(events, key=lambda e: e.timestamp, reverse=True)

"""
echotrace.integration — local shim for log_audit_trail.

Writes audit records to <repo_root>/echotrace/audit.db using SQLAlchemy.
The function signature matches every call site in the manufacturing emulator:

    log_audit_trail(
        user_id, username, action, entity_type, entity_id,
        source_system, entity_name,
        old_value=None, new_value=None, changes=None
    )

All arguments are keyword-safe.  Extra kwargs are silently ignored so
future call sites with additional fields don't break.
"""
import json
import logging
import os
import datetime
from pathlib import Path

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, create_engine, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("echotrace")

# ---------------------------------------------------------------------------
# Database setup — single shared audit.db in the echotrace/ directory
# ---------------------------------------------------------------------------
_HERE = Path(__file__).parent
_DB_PATH = _HERE / "audit.db"
_DB_URL = f"sqlite:///{_DB_PATH}"

Base = declarative_base()


class AuditLog(Base):
    """Immutable audit-trail record."""
    __tablename__ = "audit_log"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    timestamp     = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    user_id       = Column(Integer, nullable=True)
    username      = Column(String(120), nullable=True)
    action        = Column(String(50), nullable=False)       # CREATE / UPDATE / DELETE
    entity_type   = Column(String(100), nullable=False)
    entity_id     = Column(Integer, nullable=True)
    entity_name   = Column(String(255), nullable=True)
    source_system = Column(String(50), nullable=True)
    old_value     = Column(Text, nullable=True)
    new_value     = Column(Text, nullable=True)
    changes       = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id":            self.id,
            "timestamp":     self.timestamp.isoformat() if self.timestamp else None,
            "user_id":       self.user_id,
            "username":      self.username,
            "action":        self.action,
            "entity_type":   self.entity_type,
            "entity_id":     self.entity_id,
            "entity_name":   self.entity_name,
            "source_system": self.source_system,
            "old_value":     json.loads(self.old_value)  if self.old_value  else None,
            "new_value":     json.loads(self.new_value)  if self.new_value  else None,
            "changes":       json.loads(self.changes)    if self.changes    else None,
        }


# Create engine once at module load time
_engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})

# Enable WAL mode for SQLite so concurrent readers/writers don't block each other
with _engine.connect() as _conn:
    _conn.execute(text("PRAGMA journal_mode=WAL"))

Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_audit_trail(
    user_id=None,
    username=None,
    action="UPDATE",
    entity_type="Unknown",
    entity_id=None,
    source_system=None,
    entity_name=None,
    old_value=None,
    new_value=None,
    changes=None,
    **kwargs,          # absorb any extra keyword args from future call sites
):
    """
    Write one audit-trail record.

    Parameters
    ----------
    user_id       : int   — numeric user identifier (0 = system)
    username      : str   — human-readable user name
    action        : str   — CREATE | UPDATE | DELETE
    entity_type   : str   — e.g. "Order", "WorkOrder", "Material"
    entity_id     : int   — primary key of the affected record
    source_system : str   — e.g. "ERP", "MES"
    entity_name   : str   — human-readable name of the entity
    old_value     : dict  — state before the change (optional)
    new_value     : dict  — state after the change (optional)
    changes       : dict  — field-level diff (optional)
    """
    def _serialise(obj):
        if obj is None:
            return None
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return str(obj)

    session = _Session()
    try:
        record = AuditLog(
            timestamp     = datetime.datetime.utcnow(),
            user_id       = user_id,
            username      = username,
            action        = action,
            entity_type   = entity_type,
            entity_id     = entity_id,
            entity_name   = entity_name,
            source_system = source_system,
            old_value     = _serialise(old_value),
            new_value     = _serialise(new_value),
            changes       = _serialise(changes),
        )
        session.add(record)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning("echotrace: failed to write audit record: %s", exc)
    finally:
        session.close()


def get_audit_trail(
    entity_type=None,
    entity_id=None,
    source_system=None,
    limit=200,
):
    """
    Query audit records.  All filters are optional.
    Returns a list of dicts, newest first.
    """
    session = _Session()
    try:
        q = session.query(AuditLog)
        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            q = q.filter(AuditLog.entity_id == entity_id)
        if source_system:
            q = q.filter(AuditLog.source_system == source_system)
        records = q.order_by(AuditLog.id.desc()).limit(limit).all()
        return [r.to_dict() for r in records]
    finally:
        session.close()

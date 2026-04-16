"""
Persistence Utility
Provides simple JSON-based storage for all domain entities.
Each entity type is stored in a separate JSON file under the data/ directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Default data directory – can be overridden via environment variable
_DATA_DIR = Path(os.environ.get("PHARMA_DATA_DIR", Path(__file__).parent.parent / "data" / "runtime"))


def _ensure_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def _path(entity: str) -> Path:
    return _ensure_dir() / f"{entity}.json"


def load_all(entity: str, model: Type[T]) -> List[T]:
    """Load all records for an entity type."""
    p = _path(entity)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        raw: List[Dict[str, Any]] = json.load(f)
    return [model.model_validate(r) for r in raw]


def save_all(entity: str, records: List[BaseModel]) -> None:
    """Persist all records for an entity type."""
    p = _path(entity)
    with open(p, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in records], f, indent=2, default=str)


def upsert(entity: str, model: Type[T], record: T, id_field: str) -> None:
    """Insert or update a single record identified by id_field."""
    records = load_all(entity, model)
    record_id = getattr(record, id_field)
    updated = False
    for i, r in enumerate(records):
        if getattr(r, id_field) == record_id:
            records[i] = record
            updated = True
            break
    if not updated:
        records.append(record)
    save_all(entity, records)


def delete(entity: str, model: Type[T], id_field: str, record_id: str) -> bool:
    """Delete a record by ID. Returns True if found and deleted."""
    records = load_all(entity, model)
    new_records = [r for r in records if getattr(r, id_field) != record_id]
    if len(new_records) == len(records):
        return False
    save_all(entity, new_records)
    return True


def get_by_id(entity: str, model: Type[T], id_field: str, record_id: str) -> Optional[T]:
    """Retrieve a single record by its ID."""
    for r in load_all(entity, model):
        if getattr(r, id_field) == record_id:
            return r
    return None


def reset_all() -> None:
    """Delete all runtime data files (demo reset)."""
    d = _ensure_dir()
    for f in d.glob("*.json"):
        f.unlink()

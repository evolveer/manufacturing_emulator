"""
Helper Utilities
Miscellaneous utility functions used across the application.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.utcnow().isoformat()


def fmt_dt(iso: Optional[str]) -> str:
    """Format an ISO datetime string for display."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso


def status_color(status: str) -> str:
    """Return a CSS/Streamlit-compatible color hint for a status string."""
    mapping = {
        "Completed": "green",
        "Released": "green",
        "Release": "green",
        "In Progress": "blue",
        "In Execution": "blue",
        "Open": "red",
        "Critical": "red",
        "Reject / Hold": "red",
        "Rejected": "red",
        "On Hold": "orange",
        "Deviated": "orange",
        "Major": "orange",
        "Investigating": "orange",
        "Escalated": "red",
        "Minor": "yellow",
        "Approved with Justification": "green",
        "Closed": "gray",
        "Not Started": "gray",
        "Ready": "blue",
        "Skipped": "gray",
        "Under Review": "blue",
        "Release with Comments": "orange",
        "Pending": "gray",
    }
    return mapping.get(status, "gray")


def badge(status: str) -> str:
    """Return a markdown-style badge string for a status."""
    color = status_color(status)
    color_map = {
        "green": "🟢",
        "blue": "🔵",
        "red": "🔴",
        "orange": "🟠",
        "yellow": "🟡",
        "gray": "⚪",
    }
    icon = color_map.get(color, "⚪")
    return f"{icon} {status}"

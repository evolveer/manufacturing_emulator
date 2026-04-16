"""
Domain Enumerations
Defines all status and category enumerations used across the pharma batch execution simulator.
"""

from enum import Enum


class OrderStatus(str, Enum):
    CREATED = "Created"
    SENT_TO_MES = "Sent to MES"
    IN_EXECUTION = "In Execution"
    COMPLETED = "Completed"


class BatchStatus(str, Enum):
    CREATED = "Created"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    ON_HOLD = "On Hold"
    REJECTED = "Rejected"
    RELEASED = "Released"


class StepStatus(str, Enum):
    NOT_STARTED = "Not Started"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    BLOCKED = "Blocked"
    DEVIATED = "Deviated"
    SKIPPED = "Skipped"
    UNDER_REVIEW = "Under Review"


class DeviationStatus(str, Enum):
    OPEN = "Open"
    INVESTIGATING = "Investigating"
    APPROVED_WITH_JUSTIFICATION = "Approved with Justification"
    CLOSED = "Closed"
    ESCALATED = "Escalated"


class DeviationSeverity(str, Enum):
    MINOR = "Minor"
    MAJOR = "Major"
    CRITICAL = "Critical"


class DeviationCategory(str, Enum):
    OUT_OF_RANGE = "Out of Range"
    SKIPPED_STEP = "Skipped Step"
    FAILED_INSPECTION = "Failed Inspection"
    MANUAL_ENTRY = "Manual Entry"
    EQUIPMENT_FAILURE = "Equipment Failure"
    DOCUMENTATION = "Documentation"


class Disposition(str, Enum):
    PENDING = "Pending"
    RELEASE = "Release"
    RELEASE_WITH_COMMENTS = "Release with Comments"
    REJECT_HOLD = "Reject / Hold"


class ReviewStatus(str, Enum):
    NOT_STARTED = "Not Started"
    IN_REVIEW = "In Review"
    COMPLETED = "Completed"

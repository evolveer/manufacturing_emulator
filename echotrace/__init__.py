"""
echotrace — local audit-trail shim for the manufacturing emulator.

Replaces the proprietary echotrace package.  All call sites in
erp/services.py, erp/shipping_services.py, and mes/services.py use:

    from echotrace.integration import log_audit_trail

This package provides a drop-in implementation that writes records to a
shared SQLite database at <repo_root>/echotrace/audit.db.
"""

"""
Check that all service modules can be imported without errors.
Run from the repo root: python3.11 tests/check_imports.py
"""
import sys, os, importlib, traceback

CHECKS = [
    ("erp", "erp.master_data_server"),
    ("erp", "erp.api"),
    ("erp", "erp.services"),
    ("mes", "mes.main"),
    ("mes", "mes.api"),
    ("mes", "mes.services"),
    ("mes", "mes.material_services"),
    ("pcs", "pcs.main"),
    ("pcs", "pcs.api"),
    ("pcs", "pcs.services"),
    ("common", "common.interface"),
    ("common", "common.data_sync"),
]

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

errors = []
for subdir, mod in CHECKS:
    sys.path.insert(0, os.path.join(repo_root, subdir))
    try:
        importlib.import_module(mod.split(".")[-1])
        print(f"  OK  {mod}")
    except Exception as e:
        print(f"  ERR {mod}: {e}")
        errors.append((mod, traceback.format_exc()))
    finally:
        if os.path.join(repo_root, subdir) in sys.path:
            sys.path.remove(os.path.join(repo_root, subdir))

if errors:
    print("\n=== FULL TRACEBACKS ===")
    for mod, tb in errors:
        print(f"\n--- {mod} ---\n{tb}")
    sys.exit(1)
else:
    print("\nAll imports OK")

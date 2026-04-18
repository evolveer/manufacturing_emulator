"""
Database initialization script for Manufacturing Emulator System
Creates SQLite databases for ERP, MES, and PCS emulators with full demo data.

Run this script once after a fresh clone to set up all databases:
    python database/init_db.py

It is safe to re-run: all INSERT statements use INSERT OR IGNORE so existing
data is never overwritten.
"""
import os
import sqlite3
from pathlib import Path

# Always resolve paths relative to this file so the script works from any cwd
DB_DIR = Path(__file__).resolve().parent
DB_DIR.mkdir(exist_ok=True)

ERP_DB = DB_DIR / "erp.db"
MES_DB = DB_DIR / "mes.db"
PCS_DB = DB_DIR / "pcs.db"

# ─────────────────────────────────────────────────────────────────────────────
# ERP
# ─────────────────────────────────────────────────────────────────────────────

def init_erp_db():
    print("Initializing ERP database...")
    conn = sqlite3.connect(ERP_DB)
    c = conn.cursor()

    # ── Schema ────────────────────────────────────────────────────────────────
    c.executescript("""
    CREATE TABLE IF NOT EXISTS materials (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        code             TEXT    UNIQUE NOT NULL,
        name             TEXT    NOT NULL,
        description      TEXT,
        unit             TEXT    NOT NULL DEFAULT 'kg',
        cost             REAL    NOT NULL DEFAULT 0,
        stock_quantity   REAL    NOT NULL DEFAULT 0,
        min_stock_level  REAL    NOT NULL DEFAULT 0,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        code             TEXT    UNIQUE NOT NULL,
        name             TEXT    NOT NULL,
        description      TEXT,
        category         TEXT,
        price            REAL    NOT NULL DEFAULT 0,
        stock_quantity   REAL    NOT NULL DEFAULT 0,
        min_stock_level  REAL    NOT NULL DEFAULT 0,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS bom_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id  INTEGER NOT NULL REFERENCES products(id),
        material_id INTEGER NOT NULL REFERENCES materials(id),
        quantity    REAL    NOT NULL DEFAULT 0,
        UNIQUE (product_id, material_id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number  TEXT    UNIQUE NOT NULL,
        customer_name TEXT,
        status        TEXT    NOT NULL DEFAULT 'pending',
        order_date    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date      TIMESTAMP,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id   INTEGER NOT NULL REFERENCES orders(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity   REAL    NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS production_plans (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_number TEXT    UNIQUE NOT NULL,
        order_id    INTEGER REFERENCES orders(id),
        status      TEXT    NOT NULL DEFAULT 'planned',
        start_date  TIMESTAMP,
        end_date    TIMESTAMP,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS shipments (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_number    TEXT    UNIQUE NOT NULL,
        order_id           INTEGER REFERENCES orders(id),
        status             TEXT    NOT NULL DEFAULT 'pending',
        carrier            TEXT,
        tracking_number    TEXT,
        shipping_address   TEXT,
        packed_date        TIMESTAMP,
        shipped_date       TIMESTAMP,
        estimated_delivery TIMESTAMP,
        delivered_date     TIMESTAMP,
        notes              TEXT,
        created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS shipment_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        shipment_id INTEGER NOT NULL REFERENCES shipments(id),
        product_id  INTEGER NOT NULL REFERENCES products(id),
        quantity    REAL    NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS material_transactions (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id      INTEGER NOT NULL REFERENCES materials(id),
        quantity         REAL    NOT NULL,
        transaction_type TEXT    NOT NULL,
        reference_id     INTEGER,
        reference_type   TEXT,
        timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # ── Seed: Materials ───────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO materials (code, name, description, unit, cost, stock_quantity, min_stock_level) VALUES (?,?,?,?,?,?,?)",
        [
            ("PP-GF30",       "Polypropylene 30% Glass Filled",   "High-strength PP with 30% glass fiber reinforcement", "kg", 4.2,  945.0, 200.0),
            ("ABS-FR",        "ABS Flame Retardant",              "ABS with flame retardant additives for electronics",  "kg", 5.8,  800.0, 150.0),
            ("PA66-GF30",     "Polyamide 66 30% Glass Filled",    "High-temperature PA66 with glass fiber",              "kg", 8.5,  598.0, 100.0),
            ("PC-CLEAR",      "Polycarbonate Clear",              "Transparent polycarbonate for optical components",    "kg", 6.5,  400.0,  80.0),
            ("TPE-SOFT",      "Thermoplastic Elastomer Soft",     "Soft TPE for overmolding applications",               "kg", 7.2,  296.0,  50.0),
            ("API-PARA-001",  "Paracetamol API",                  "Active pharmaceutical ingredient – paracetamol",      "kg", 45.0, 500.0,  50.0),
            ("EXCIP-MCC-001", "Microcrystalline Cellulose",       "Pharmaceutical excipient – tablet binder/filler",     "kg", 12.0,1000.0, 100.0),
        ]
    )

    # ── Seed: Products ────────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO products (code, name, description, category, price, stock_quantity, min_stock_level) VALUES (?,?,?,?,?,?,?)",
        [
            ("HOUSING-A",  "Electronic Housing Type A",        "Plastic housing for electronic devices",          "Housings",       12.5,  0.0, 0.0),
            ("GEAR-B",     "Precision Gear Type B",            "High precision gear for mechanical systems",      "Mechanical",      8.75, 0.0, 0.0),
            ("COVER-C",    "Transparent Cover Type C",         "Clear cover for displays",                        "Covers",         15.3,  0.0, 0.0),
            ("HANDLE-D",   "Ergonomic Handle Type D",          "Soft-touch handle with overmolding",              "Handles",         9.2,  0.0, 0.0),
            ("BRACKET-E",  "Mounting Bracket Type E",          "Reinforced mounting bracket",                     "Brackets",        6.8,  0.0, 0.0),
            ("SEAL-F",     "Sealing Ring Type F",              "High-temp sealing ring",                          "Seals",           4.5,  0.0, 0.0),
            ("TAB-500MG",  "Metformin Tablet 500mg",           "Pharma product – Metformin Tablet 500mg",         "Pharmaceutical",  0.0,  0.0, 0.0),
            ("TAB-500MG-2","Metformin Tablet 500mg (batch 2)", "Pharma product – Metformin Tablet 500mg batch 2", "Pharmaceutical",  0.0,  0.0, 0.0),
            ("INJ-10MG",   "Ondansetron Injection 10mg/mL",    "Pharma product – Ondansetron Injection 10mg/mL",  "Pharmaceutical",  0.0,  0.0, 0.0),
        ]
    )

    # ── Seed: BOM items ───────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO bom_items (product_id, material_id, quantity) VALUES (?,?,?)",
        [
            (1, 1, 0.25),
            (2, 3, 0.10),
            (3, 4, 0.15),
            (4, 5, 0.20),
            (5, 1, 0.18),
        ]
    )

    # ── Seed: Orders ──────────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO orders (order_number, customer_name, status) VALUES (?,?,?)",
        [
            ("ORD-DEMO-001", "Pharma – Site A",    "completed"),
            ("ORD-DEMO-002", "Pharma – Site A",    "completed"),
            ("ORD-DEMO-003", "Pharma – Site A",    "completed"),
            ("ORD-DEMO-004", "Pharma – Site A",    "in_production"),
            ("ORD-DEMO-005", "Pharma – Site B",    "in_production"),
            ("ORD-DEMO-006", "Pharma – Site B",    "pending"),
            ("ORD-DEMO-007", "Acme Corp",          "completed"),
            ("ORD-DEMO-008", "Acme Corp",          "completed"),
            ("ORD-DEMO-009", "Acme Corp",          "in_production"),
            ("ORD-DEMO-010", "Global Devices Ltd", "pending"),
        ]
    )

    # ── Seed: Order items ─────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO order_items (order_id, product_id, quantity) VALUES (?,?,?)",
        [
            (1, 7, 15000),
            (2, 7, 15000),
            (3, 9, 1000),
            (4, 7, 15000),
            (5, 9, 2000),
            (6, 7, 10000),
            (7, 1, 5000),
            (8, 2, 3000),
            (9, 1, 8000),
            (10, 3, 2000),
        ]
    )

    # ── Seed: Production plans ────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO production_plans (plan_number, order_id, status) VALUES (?,?,?)",
        [
            ("PP-ORD-DEMO-001", 1, "completed"),
            ("PP-ORD-DEMO-002", 2, "completed"),
            ("PP-ORD-DEMO-003", 3, "completed"),
            ("PP-ORD-DEMO-004", 4, "in_progress"),
            ("PP-ORD-DEMO-005", 5, "in_progress"),
            ("PP-ORD-DEMO-006", 6, "planned"),
            ("PP-ORD-DEMO-007", 7, "completed"),
            ("PP-ORD-DEMO-008", 8, "completed"),
            ("PP-ORD-DEMO-009", 9, "in_progress"),
            ("PP-ORD-DEMO-010", 10, "planned"),
        ]
    )

    conn.commit()
    conn.close()
    print("  ERP database initialized successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# MES
# ─────────────────────────────────────────────────────────────────────────────

def init_mes_db():
    print("Initializing MES database...")
    conn = sqlite3.connect(MES_DB)
    c = conn.cursor()

    # ── Schema ────────────────────────────────────────────────────────────────
    c.executescript("""
    CREATE TABLE IF NOT EXISTS machines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_code TEXT    UNIQUE NOT NULL,
        name         TEXT    NOT NULL,
        type         TEXT    NOT NULL DEFAULT 'injection_molding',
        status       TEXT    NOT NULL DEFAULT 'idle',
        location     TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS production_plans (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_number TEXT    UNIQUE NOT NULL,
        order_id    INTEGER,
        status      TEXT    NOT NULL DEFAULT 'planned',
        start_date  TIMESTAMP,
        end_date    TIMESTAMP,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS work_orders (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_number   TEXT    UNIQUE NOT NULL,
        production_plan_id  INTEGER REFERENCES production_plans(id),
        product_id          INTEGER NOT NULL DEFAULT 1,
        product_name        TEXT,
        quantity            REAL    NOT NULL DEFAULT 0,
        status              TEXT    NOT NULL DEFAULT 'planned',
        start_time          TIMESTAMP,
        end_time            TIMESTAMP,
        machine_id          INTEGER REFERENCES machines(id),
        inventory_posted    BOOLEAN NOT NULL DEFAULT 0,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS quality_checks (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id  INTEGER NOT NULL REFERENCES work_orders(id),
        check_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parameter      TEXT    NOT NULL,
        value          REAL    NOT NULL DEFAULT 0,
        min_value      REAL,
        max_value      REAL,
        status         TEXT    NOT NULL DEFAULT 'pass',
        inspector      TEXT,
        notes          TEXT
    );

    CREATE TABLE IF NOT EXISTS production_counts (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id  INTEGER NOT NULL REFERENCES work_orders(id),
        count_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        good_count     INTEGER NOT NULL DEFAULT 0,
        reject_count   INTEGER NOT NULL DEFAULT 0,
        rework_count   INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS production_schedule (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id      INTEGER NOT NULL REFERENCES machines(id),
        work_order_id   INTEGER NOT NULL REFERENCES work_orders(id),
        scheduled_start TIMESTAMP,
        scheduled_end   TIMESTAMP,
        priority        INTEGER DEFAULT 5,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS materials (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT    UNIQUE NOT NULL,
        name         TEXT    NOT NULL,
        quantity     REAL    NOT NULL DEFAULT 0,
        min_quantity REAL    NOT NULL DEFAULT 0,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS material_tracking (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id    INTEGER NOT NULL REFERENCES work_orders(id),
        material_id      INTEGER NOT NULL REFERENCES materials(id),
        planned_quantity REAL    NOT NULL DEFAULT 0,
        actual_quantity  REAL    NOT NULL DEFAULT 0,
        transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        transaction_type TEXT    NOT NULL DEFAULT 'consumption'
    );

    CREATE TABLE IF NOT EXISTS downtimes (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id     INTEGER NOT NULL REFERENCES machines(id),
        work_order_id  INTEGER REFERENCES work_orders(id),
        start_time     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        end_time       TIMESTAMP,
        reason         TEXT    NOT NULL,
        category       TEXT    NOT NULL,
        notes          TEXT
    );
    """)

    # ── Seed: Machines ────────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO machines (machine_code, name, type, status, location) VALUES (?,?,?,?,?)",
        [
            ("IMM-100",        "Injection Molding Machine 100T",  "injection_molding", "idle",        "Production Hall A"),
            ("IMM-200",        "Injection Molding Machine 200T",  "injection_molding", "in_progress", "Production Hall A"),
            ("IMM-300",        "Injection Molding Machine 300T",  "injection_molding", "maintenance", "Production Hall B"),
            ("TABLET-PRESS-01","Tablet Press 01",                 "tablet_press",      "idle",        "Suite A"),
            ("TABLET-PRESS-02","Tablet Press 02",                 "tablet_press",      "in_progress", "Suite A"),
            ("COATING-01",     "Tablet Coater 01",                "tablet_coater",     "idle",        "Suite B"),
            ("FILLING-01",     "Vial Filling Line 01",            "filling",           "in_progress", "Suite C"),
            ("FILLING-02",     "Vial Filling Line 02",            "filling",           "idle",        "Suite C"),
            ("GRANULATOR-01",  "High Shear Granulator 01",        "granulator",        "idle",        "Suite A"),
            ("GRANULATOR-02",  "High Shear Granulator 02",        "granulator",        "idle",        "Suite A"),
        ]
    )

    # ── Seed: Production plans ────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO production_plans (plan_number, order_id, status) VALUES (?,?,?)",
        [
            ("PP-ORD-DEMO-001", 1, "completed"),
            ("PP-ORD-DEMO-002", 2, "completed"),
            ("PP-ORD-DEMO-003", 3, "completed"),
            ("PP-ORD-DEMO-004", 4, "in_progress"),
            ("PP-ORD-DEMO-005", 5, "in_progress"),
            ("PP-ORD-DEMO-006", 6, "planned"),
            ("PP-ORD-DEMO-007", 7, "completed"),
            ("PP-ORD-DEMO-008", 8, "completed"),
            ("PP-ORD-DEMO-009", 9, "in_progress"),
            ("PP-ORD-DEMO-010", 10, "planned"),
        ]
    )

    # ── Seed: Work orders ─────────────────────────────────────────────────────
    c.executemany(
        """INSERT OR IGNORE INTO work_orders
           (work_order_number, production_plan_id, product_id, product_name, quantity, status, machine_id, inventory_posted)
           VALUES (?,?,?,?,?,?,?,?)""",
        [
            ("WO-DEMO-001", 1, 7, "Metformin Tablet 500mg",         15000, "completed",   1, 1),
            ("WO-DEMO-002", 2, 7, "Metformin Tablet 500mg",         15000, "completed",   1, 1),
            ("WO-DEMO-003", 3, 9, "Ondansetron Injection 10mg/mL",   1000, "completed",   7, 1),
            ("WO-DEMO-004", 4, 7, "Metformin Tablet 500mg",         15000, "in_progress", 2, 0),
            ("WO-DEMO-005", 5, 9, "Ondansetron Injection 10mg/mL",   2000, "in_progress", 7, 0),
            ("WO-DEMO-006", 6, 7, "Metformin Tablet 500mg",         10000, "planned",     4, 0),
            ("WO-DEMO-007", 7, 1, "Electronic Housing Type A",       5000, "completed",   1, 1),
            ("WO-DEMO-008", 8, 2, "Precision Gear Type B",           3000, "completed",   2, 1),
            ("WO-DEMO-009", 9, 1, "Electronic Housing Type A",       8000, "in_progress", 1, 0),
            ("WO-DEMO-010",10, 3, "Transparent Cover Type C",        2000, "planned",     3, 0),
        ]
    )

    # ── Seed: Quality checks ──────────────────────────────────────────────────
    quality_checks = []
    for wo_id, checks in [
        (1, [("tablet_weight", 502.1, 490.0, 510.0, "pass"),
             ("hardness",       8.2,   7.0,  12.0, "pass"),
             ("dissolution",   85.5,  80.0, 100.0, "pass"),
             ("disintegration", 4.2,   0.0,   5.0, "pass")]),
        (2, [("tablet_weight", 498.7, 490.0, 510.0, "pass"),
             ("hardness",       9.1,   7.0,  12.0, "pass"),
             ("dissolution",   88.3,  80.0, 100.0, "pass"),
             ("disintegration", 3.8,   0.0,   5.0, "pass")]),
        (3, [("fill_volume",   10.05,  9.8,  10.2, "pass"),
             ("particulates",   0.0,   0.0,   2.0, "pass"),
             ("sterility",      1.0,   1.0,   1.0, "pass")]),
        (4, [("tablet_weight", 505.2, 490.0, 510.0, "pass"),
             ("hardness",       7.8,   7.0,  12.0, "pass"),
             ("dissolution",   79.1,  80.0, 100.0, "fail"),
             ("disintegration", 5.8,   0.0,   5.0, "fail")]),
        (5, [("fill_volume",    9.75,  9.8,  10.2, "fail"),
             ("particulates",   0.0,   0.0,   2.0, "pass"),
             ("sterility",      1.0,   1.0,   1.0, "pass")]),
        (7, [("weight",        25.1,  24.5,  25.5, "pass"),
             ("dimensions",     1.0,   1.0,   1.0, "pass")]),
        (8, [("runout",         0.02,  0.0,   0.05, "pass"),
             ("hardness",      58.0,  55.0,  65.0, "pass")]),
        (9, [("weight",        25.3,  24.5,  25.5, "pass"),
             ("dimensions",     1.0,   1.0,   1.0, "pass")]),
    ]:
        for param, val, mn, mx, status in checks:
            quality_checks.append((wo_id, param, val, mn, mx, status, "QA-001", f"[auto] {param} check"))

    c.executemany(
        "INSERT OR IGNORE INTO quality_checks (work_order_id, parameter, value, min_value, max_value, status, inspector, notes) VALUES (?,?,?,?,?,?,?,?)",
        quality_checks
    )

    # ── Seed: Production counts ───────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO production_counts (work_order_id, good_count, reject_count, rework_count) VALUES (?,?,?,?)",
        [
            (1, 14850, 150, 0),
            (2, 14920,  80, 0),
            (3,   980,  20, 0),
            (4,  8000, 200, 50),
            (5,  1200,  80, 20),
            (7,  4900, 100, 0),
            (8,  2980,  20, 0),
        ]
    )

    # ── Seed: Production schedule ─────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO production_schedule (machine_id, work_order_id, priority) VALUES (?,?,?)",
        [
            (2, 4, 1),
            (7, 5, 1),
            (4, 6, 2),
            (1, 9, 1),
            (3, 10, 3),
        ]
    )

    conn.commit()
    conn.close()
    print("  MES database initialized successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# PCS
# ─────────────────────────────────────────────────────────────────────────────

def init_pcs_db():
    print("Initializing PCS database...")
    conn = sqlite3.connect(PCS_DB)
    c = conn.cursor()

    # ── Schema ────────────────────────────────────────────────────────────────
    c.executescript("""
    CREATE TABLE IF NOT EXISTS machine_commands (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id   INTEGER NOT NULL,
        command_type TEXT    NOT NULL,
        parameters   TEXT,
        timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status       TEXT    NOT NULL DEFAULT 'pending',
        response     TEXT
    );

    CREATE TABLE IF NOT EXISTS machine_parameters (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id     INTEGER NOT NULL,
        parameter_name TEXT    NOT NULL,
        current_value  REAL,
        set_point      REAL,
        min_value      REAL,
        max_value      REAL,
        unit           TEXT,
        updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (machine_id, parameter_name)
    );

    CREATE TABLE IF NOT EXISTS sensor_data (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id  INTEGER NOT NULL,
        sensor_name TEXT    NOT NULL,
        value       REAL    NOT NULL,
        timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        quality     INTEGER DEFAULT 100
    );

    CREATE TABLE IF NOT EXISTS alarms (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id   INTEGER NOT NULL,
        alarm_code   TEXT    NOT NULL,
        description  TEXT    NOT NULL,
        severity     TEXT    NOT NULL DEFAULT 'info',
        status       TEXT    NOT NULL DEFAULT 'active',
        start_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time     TIMESTAMP,
        acknowledged BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS machine_states (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id     INTEGER NOT NULL,
        state          TEXT    NOT NULL DEFAULT 'idle',
        start_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time       TIMESTAMP,
        work_order_id  INTEGER,
        cycle_count    INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS cycle_data (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id     INTEGER NOT NULL,
        work_order_id  INTEGER,
        cycle_number   INTEGER NOT NULL,
        start_time     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        end_time       TIMESTAMP,
        cycle_time     REAL,
        status         TEXT    DEFAULT 'completed'
    );
    """)

    # ── Seed: Machine parameters ──────────────────────────────────────────────
    params = []
    # Injection molding machines (PCS machine IDs 1-3 mirror MES machine IDs)
    for mid, sp in [(1, (215, 125, 100, 55)), (2, (225, 150, 120, 60)), (3, (210, 120, 90, 50))]:
        t, p, cf, inj = sp
        params += [
            (mid, "temperature",     t,   t,   180.0, 250.0, "celsius"),
            (mid, "pressure",        p,   p,    50.0, 200.0, "bar"),
            (mid, "clamp_force",     cf,  cf,   50.0, 150.0, "tons"),
            (mid, "injection_speed", inj, inj,  10.0, 100.0, "mm/s"),
        ]
    # Pharma machines (machine IDs 4-10)
    for mid in [4, 5, 6, 7, 8, 9, 10]:
        params += [
            (mid, "temperature", 25.0,  25.0,  18.0,  30.0, "celsius"),
            (mid, "pressure",    1.013, 1.013,  0.9,   1.1, "bar"),
            (mid, "speed",       60.0,  60.0,  20.0, 120.0, "rpm"),
            (mid, "humidity",    45.0,  45.0,  30.0,  60.0, "percent"),
        ]

    c.executemany(
        """INSERT OR IGNORE INTO machine_parameters
           (machine_id, parameter_name, current_value, set_point, min_value, max_value, unit)
           VALUES (?,?,?,?,?,?,?)""",
        params
    )

    # ── Seed: Machine states ──────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO machine_states (machine_id, state, work_order_id, cycle_count) VALUES (?,?,?,?)",
        [
            (1, "idle",    None, 0),
            (2, "running", 4,    250),
            (3, "idle",    None, 0),
            (4, "idle",    None, 0),
            (5, "running", 5,    180),
            (6, "idle",    None, 0),
            (7, "running", 5,    90),
            (8, "idle",    None, 0),
            (9, "idle",    None, 0),
            (10, "idle",   None, 0),
        ]
    )

    # ── Seed: Alarms ──────────────────────────────────────────────────────────
    c.executemany(
        "INSERT OR IGNORE INTO alarms (machine_id, alarm_code, description, severity, status) VALUES (?,?,?,?,?)",
        [
            (3, "MOLD_WEAR",   "Mold wear detected, maintenance recommended", "info",    "active"),
            (1, "EJECTOR_JAM", "Part ejector mechanism jammed",               "error",   "active"),
            (9, "TEMP_HIGH",   "Temperature exceeds recommended range",        "warning", "active"),
        ]
    )

    # ── Seed: Cycle data (sample completed cycles) ────────────────────────────
    cycles = []
    for i in range(1, 21):
        cycles.append((2, 4, i, f"2026-04-18 06:{i:02d}:00", f"2026-04-18 06:{i:02d}:45", 45.2, "completed"))
    for i in range(1, 11):
        cycles.append((5, 5, i, f"2026-04-18 07:{i:02d}:00", f"2026-04-18 07:{i:02d}:30", 30.5, "completed"))
    for i in range(1, 6):
        cycles.append((7, 5, i, f"2026-04-18 07:{i:02d}:05", f"2026-04-18 07:{i:02d}:35", 30.1, "completed"))

    c.executemany(
        "INSERT OR IGNORE INTO cycle_data (machine_id, work_order_id, cycle_number, start_time, end_time, cycle_time, status) VALUES (?,?,?,?,?,?,?)",
        cycles
    )

    # ── Seed: Sensor data ─────────────────────────────────────────────────────
    sensors = []
    for mid in [1, 2, 3]:
        sensors += [
            (mid, "position",           100.0 + mid, "2026-04-18 08:00:00", 100),
            (mid, "hydraulic_pressure",  118.0 + mid, "2026-04-18 08:00:01", 100),
            (mid, "mold_temperature",    215.0 + mid, "2026-04-18 08:00:02", 100),
        ]
    for mid in [4, 5, 6, 7, 8, 9, 10]:
        sensors += [
            (mid, "temperature", 25.0 + mid * 0.1, "2026-04-18 08:00:00", 100),
            (mid, "humidity",    45.0 + mid * 0.2, "2026-04-18 08:00:01", 100),
        ]
    c.executemany(
        "INSERT OR IGNORE INTO sensor_data (machine_id, sensor_name, value, timestamp, quality) VALUES (?,?,?,?,?)",
        sensors
    )

    conn.commit()
    conn.close()
    print("  PCS database initialized successfully.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Manufacturing Emulator – Database Initialization")
    print("=" * 60)
    init_erp_db()
    init_mes_db()
    init_pcs_db()
    print("=" * 60)
    print("All databases initialized successfully.")
    print(f"  ERP : {ERP_DB}")
    print(f"  MES : {MES_DB}")
    print(f"  PCS : {PCS_DB}")
    print("=" * 60)

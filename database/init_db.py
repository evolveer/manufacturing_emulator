"""
Database initialization script for Manufacturing Emulator System
Creates SQLite databases for ERP, MES, and PCS emulators
"""
import os
import sys
import sqlite3
from pathlib import Path

# Ensure we're in the project root directory
project_root = Path(__file__).parent.absolute()
os.chdir(project_root)

# Create database directory if it doesn't exist
db_dir = project_root / "database"
db_dir.mkdir(exist_ok=True)

# Initialize ERP database
def init_erp_db():
    print("Initializing ERP database...")
    conn = sqlite3.connect(db_dir / "erp.db")
    cursor = conn.cursor()
    
    # Create Materials table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        unit TEXT NOT NULL,
        cost REAL NOT NULL,
        stock_quantity REAL NOT NULL DEFAULT 0,
        min_stock_level REAL NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        category TEXT,
        price REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create BOM (Bill of Materials) table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bom_items (
        id INTEGER PRIMARY KEY,
        product_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products (id),
        FOREIGN KEY (material_id) REFERENCES materials (id),
        UNIQUE (product_id, material_id)
    )
    ''')
    
    # Create Orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        order_number TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        status TEXT NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        due_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Order Items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')
    
    # Create Production Plans table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_plans (
        id INTEGER PRIMARY KEY,
        plan_number TEXT UNIQUE NOT NULL,
        order_id INTEGER,
        status TEXT NOT NULL,
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (id)
    )
    ''')
    
    # Insert sample data for materials
    cursor.execute('''
    INSERT OR IGNORE INTO materials (code, name, description, unit, cost, stock_quantity, min_stock_level)
    VALUES 
        ('PP-GF30', 'Polypropylene 30% Glass Filled', 'Glass-filled polypropylene for injection molding', 'kg', 3.50, 1000, 200),
        ('ABS-FR', 'ABS Flame Retardant', 'Flame retardant ABS for injection molding', 'kg', 4.20, 800, 150),
        ('PA66-GF30', 'Polyamide 66 30% Glass Filled', 'Glass-filled nylon for high strength parts', 'kg', 5.80, 600, 100),
        ('PC-CLEAR', 'Polycarbonate Clear', 'Transparent polycarbonate for optical components', 'kg', 6.50, 400, 80),
        ('TPE-SOFT', 'Thermoplastic Elastomer Soft', 'Soft TPE for overmolding applications', 'kg', 7.20, 300, 50)
    ''')
    
    # Insert sample data for products
    cursor.execute('''
    INSERT OR IGNORE INTO products (code, name, description, category, price)
    VALUES 
        ('HOUSING-A', 'Electronic Housing Type A', 'Plastic housing for electronic devices', 'Housings', 12.50),
        ('GEAR-B', 'Precision Gear Type B', 'High precision gear for mechanical systems', 'Mechanical', 8.75),
        ('COVER-C', 'Transparent Cover Type C', 'Clear cover for displays', 'Covers', 15.30),
        ('HANDLE-D', 'Ergonomic Handle Type D', 'Soft-touch handle with overmolding', 'Handles', 9.20),
        ('BRACKET-E', 'Mounting Bracket Type E', 'Reinforced mounting bracket', 'Brackets', 6.80)
    ''')
    
    # Insert sample BOM data
    cursor.execute('''
    INSERT OR IGNORE INTO bom_items (product_id, material_id, quantity)
    VALUES 
        (1, 1, 0.25),  -- Housing A uses 0.25kg of PP-GF30
        (2, 3, 0.10),  -- Gear B uses 0.10kg of PA66-GF30
        (3, 4, 0.15),  -- Cover C uses 0.15kg of PC-CLEAR
        (4, 5, 0.20),  -- Handle D uses 0.20kg of TPE-SOFT
        (5, 1, 0.18)   -- Bracket E uses 0.18kg of PP-GF30
    ''')
    
    conn.commit()
    conn.close()
    print("ERP database initialized successfully.")

# Initialize MES database
def init_mes_db():
    print("Initializing MES database...")
    conn = sqlite3.connect(db_dir / "mes.db")
    cursor = conn.cursor()
    
    # Create Work Orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS work_orders (
        id INTEGER PRIMARY KEY,
        work_order_number TEXT UNIQUE NOT NULL,
        production_plan_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        machine_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Machines table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS machines (
        id INTEGER PRIMARY KEY,
        machine_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        status TEXT NOT NULL,
        location TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create Production Schedule table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_schedule (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        work_order_id INTEGER NOT NULL,
        scheduled_start TIMESTAMP NOT NULL,
        scheduled_end TIMESTAMP NOT NULL,
        priority INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (machine_id) REFERENCES machines (id),
        FOREIGN KEY (work_order_id) REFERENCES work_orders (id)
    )
    ''')
    
    # Create Quality Control table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quality_checks (
        id INTEGER PRIMARY KEY,
        work_order_id INTEGER NOT NULL,
        check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        parameter TEXT NOT NULL,
        value REAL NOT NULL,
        min_value REAL,
        max_value REAL,
        status TEXT NOT NULL,
        inspector TEXT,
        notes TEXT,
        FOREIGN KEY (work_order_id) REFERENCES work_orders (id)
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS material_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        planned_quantity REAL DEFAULT 0,
        actual_quantity REAL DEFAULT 0,
        transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('consumption', 'return', 'waste')),
        FOREIGN KEY (work_order_id) REFERENCES work_orders (id),
        FOREIGN KEY (material_id) REFERENCES materials (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_counts (
        id INTEGER PRIMARY KEY,
        work_order_id INTEGER NOT NULL,
        count_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        good_count INTEGER DEFAULT 0,
        reject_count INTEGER DEFAULT 0,
        rework_count INTEGER DEFAULT 0,
        FOREIGN KEY (work_order_id) REFERENCES work_orders (id)
    )
    ''')
    
    # Create Production Plans table (needed for MES operations)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_plans (
        id INTEGER PRIMARY KEY,
        plan_number TEXT UNIQUE NOT NULL,
        order_id INTEGER,
        status TEXT NOT NULL,
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')


    # Insert sample data for machines
    cursor.execute('''
    INSERT OR IGNORE INTO machines (machine_code, name, type, status, location)
    VALUES 
        ('IMM-100', 'Injection Molding Machine 100T', 'injection_molding', 'idle', 'Production Hall A'),
        ('IMM-200', 'Injection Molding Machine 200T', 'injection_molding', 'idle', 'Production Hall A'),
        ('IMM-300', 'Injection Molding Machine 300T', 'injection_molding', 'maintenance', 'Production Hall B')
    ''')
        # Create Materials table (needed for ERP → MES sync)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        quantity REAL NOT NULL DEFAULT 0,
        min_quantity REAL NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()
    print("MES database initialized successfully.")

# Initialize PCS database
def init_pcs_db():
    print("Initializing PCS database...")
    conn = sqlite3.connect(db_dir / "pcs.db")
    cursor = conn.cursor()
    
    # Create Machine Parameters table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS machine_parameters (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        parameter_name TEXT NOT NULL,
        current_value REAL,
        set_point REAL,
        min_value REAL,
        max_value REAL,
        unit TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (machine_id, parameter_name)
    )
    ''')
    
    # Create Sensor Data table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        sensor_name TEXT NOT NULL,
        value REAL NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        quality INTEGER DEFAULT 100
    )
    ''')
    
    # Create Alarms table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alarms (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        alarm_code TEXT NOT NULL,
        description TEXT NOT NULL,
        severity TEXT NOT NULL,
        status TEXT NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        acknowledged BOOLEAN DEFAULT 0
    )
    ''')
    
    # Create Machine States table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS machine_states (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        state TEXT NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        work_order_id INTEGER,
        cycle_count INTEGER DEFAULT 0
    )
    ''')
    
    # Insert sample data for machine parameters
    cursor.execute('''
    INSERT OR IGNORE INTO machine_parameters (machine_id, parameter_name, current_value, set_point, min_value, max_value, unit)
    VALUES 
        (1, 'temperature', 200, 200, 180, 250, 'celsius'),
        (1, 'pressure', 120, 120, 50, 200, 'bar'),
        (1, 'clamp_force', 90, 90, 50, 150, 'tons'),
        (1, 'injection_speed', 50, 50, 10, 100, 'mm/s'),
        (2, 'temperature', 220, 220, 180, 250, 'celsius'),
        (2, 'pressure', 150, 150, 50, 200, 'bar'),
        (2, 'clamp_force', 120, 120, 50, 150, 'tons'),
        (2, 'injection_speed', 60, 60, 10, 100, 'mm/s')
    ''')
    
    conn.commit()
    conn.close()
    print("PCS database initialized successfully.")

if __name__ == "__main__":
    print("Initializing databases for Manufacturing Emulator System...")
    init_erp_db()
    init_mes_db()
    init_pcs_db()
    print("All databases initialized successfully.")

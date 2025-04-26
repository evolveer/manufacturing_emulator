#!/bin/bash

# Shutdown script for Manufacturing Emulator System
# This script stops all components of the manufacturing emulator system

echo "Stopping Manufacturing Emulator System..."

# Function to stop a component
stop_component() {
    component=$1
    if [ -f logs/$component.pid ]; then
        pid=$(cat logs/$component.pid)
        echo "Stopping $component (PID: $pid)..."
        kill $pid 2>/dev/null || true
        rm logs/$component.pid
        echo "$component stopped"
    else
        echo "$component not running"
    fi
}

# Stop Interface
stop_component "common"

# Stop PCS
stop_component "pcs"

# Stop MES
stop_component "mes"

# Stop ERP
stop_component "erp"

echo "All components stopped"

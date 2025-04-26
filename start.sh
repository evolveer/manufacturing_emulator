#!/bin/bash

# Startup script for Manufacturing Emulator System
# This script starts all components of the manufacturing emulator system

echo "Starting Manufacturing Emulator System..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to start a component
start_component() {
    component=$1
    port=$2
    echo "Starting $component on port $port..."
    python3 $component/main.py > logs/$component.log 2>&1 &
    echo $! > logs/$component.pid
    echo "$component started with PID $(cat logs/$component.pid)"
}

# Start ERP
start_component "erp" 5001

# Wait a moment to ensure ERP is up
sleep 2

# Start MES
start_component "mes" 5002

# Wait a moment to ensure MES is up
sleep 2

# Start PCS
start_component "pcs" 5003

# Wait a moment to ensure PCS is up
sleep 2

# Start Interface
start_component "common" 5000

echo "All components started. Access the unified interface at http://localhost:5000"
echo "Use ./stop.sh to stop all components"

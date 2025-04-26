#!/bin/bash

# Enhanced start script for Manufacturing Emulator System
# This script includes additional checks and error handling

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "Warning: Port $port is already in use. This may cause conflicts."
        return 1
    fi
    return 0
}

# Function to start a component with error handling
start_component() {
    component=$1
    port=$2
    
    echo "Starting $component on port $port..."
    
    # Check if port is available
    check_port $port
    
    # Create log file
    touch logs/$component.log
    
    if [ "$component" = "common" ]; then
        # Special case for interface component
        if [ -f common/interface.py ]; then
            python3 common/interface.py > logs/interface.log 2>&1 &
            echo $! > logs/interface.pid
            echo "$component started with PID $(cat logs/interface.pid)"
        else
            echo "Error: interface.py not found in common directory"
            return 1
        fi
    else
        # Normal case for other components
        if [ -f $component/main.py ]; then
            python3 $component/main.py > logs/$component.log 2>&1 &
            echo $! > logs/$component.pid
            echo "$component started with PID $(cat logs/$component.pid)"
        else
            echo "Error: main.py not found in $component directory"
            return 1
        fi
    fi
    
    # Wait a moment to ensure process starts
    sleep 2
    
    # Verify process is still running
    if [ -f logs/$component.pid ]; then
        pid=$(cat logs/$component.pid)
        if ps -p $pid > /dev/null; then
            echo "$component is running correctly"
        else
            echo "Warning: $component process started but exited immediately. Check logs/$([ "$component" = "common" ] && echo "interface" || echo "$component").log for errors."
        fi
    fi
}
# Initialize databases if needed
if [ ! -f database/database/erp.db ] || [ ! -f database/database/mes.db ] || [ ! -f database/database/pcs.db ]; then
    echo "Initializing databases..."
    mkdir -p database/database
    if [ -f database/init_db.py ]; then
        python3 database/init_db.py
    else
        echo "Warning: Database initialization script not found"
    fi
fi

# Start all components
echo "Starting Manufacturing Emulator System..."
start_component "erp" 5001
start_component "mes" 5002
start_component "pcs" 5003
start_component "common" 5000

# Verify all components are running
echo "Verifying all components..."
all_running=true
for component in erp mes pcs common; do
    pid_file="logs/$([ "$component" = "common" ] && echo "interface" || echo "$component").pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ! ps -p $pid > /dev/null; then
            echo "Error: $component is not running"
            all_running=false
        fi
    else
        echo "Error: PID file for $component not found"
        all_running=false
    fi
done

if $all_running; then
    echo "All components started successfully."
    echo "You can access the system at:"
    echo "- Main dashboard: http://localhost:5000"
    echo "- ERP interface: http://localhost:5001"
    echo "- MES interface: http://localhost:5002"
    echo "- PCS interface: http://localhost:5003"
else
    echo "Some components failed to start. Check the logs for details."
fi

echo "Use ./stop.sh to stop all components."

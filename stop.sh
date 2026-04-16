#!/bin/bash

echo "Stopping Manufacturing Emulator System..."

cd ./
# Function to stop a service
stop_service() {
    local pid_file=$1
    local name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            kill $pid
            echo "✓ Stopped $name (PID: $pid)"
        else
            echo "✗ $name was not running"
        fi
        rm -f "$pid_file"
    else
        echo "✗ No PID file found for $name"
    fi
}

# Stop all services
stop_service "logs/pharma.pid" "Pharma Batch Simulator"
stop_service "logs/interface.pid" "Unified Interface"
stop_service "logs/echotrace.pid" "EchoTrace Service"
stop_service "logs/pcs.pid" "PCS Service"
stop_service "logs/mes.pid" "MES Service"
stop_service "logs/erp.pid" "ERP Service"


echo ""
echo "=================================================="
echo "System stopped successfully!"
echo "=================================================="

#!/bin/bash

echo "Starting Enhanced Manufacturing Emulator System..."
echo "=================================================="

cd ./

# Create logs directory if it doesn't exist
mkdir -p logs

# Start ERP Service (with Master Data UI)
echo "Starting ERP Service (Master Data) on port 5001..."
nohup python3 erp/master_data_server.py > logs/erp.log 2>&1 & echo $! > logs/erp.pid
sleep 2

# Start MES Service
echo "Starting MES Service on port 5002..."
nohup python3 mes/main.py > logs/mes.log 2>&1 & echo $! > logs/mes.pid
sleep 2

# Start PCS Service
echo "Starting PCS Service on port 5003..."
nohup python3 pcs/main.py > logs/pcs.log 2>&1 & echo $! > logs/pcs.pid
sleep 2

# Start Unified Interface
echo "Starting Unified Interface on port 5000..."
nohup python3 common/interface.py > logs/interface.log 2>&1 & echo $! > logs/interface.pid
sleep 3

# Check if services are running
echo ""
echo "Checking service status..."
echo "=================================================="

check_service() {
    local port=$1
    local name=$2
    if curl -s http://localhost:$port/api/v1/status > /dev/null 2>&1; then
        echo "✓ $name is running on port $port"
    else
        echo "✗ $name failed to start on port $port"
    fi
}

check_service 5001 "ERP"
check_service 5002 "MES"
check_service 5003 "PCS"
check_service 5000 "Interface"

echo ""
echo "=================================================="
echo "System started successfully!"
echo ""
echo "Access the system at: http://localhost:5000"
echo ""
echo "Available pages:"
echo "  - Main Dashboard:    http://localhost:5000/"
echo "  - Order Workflow:    http://localhost:5000/order-workflow"
echo "  - PCS (Alarms):      http://localhost:5000/pcs"
echo "  - ERP Dashboard:     http://localhost:5000/erp"
echo "  - MES Dashboard:     http://localhost:5000/mes"
echo "ERP Master Data UI: http://localhost:5001/master_data"
echo ""
echo "To stop the system, run: ./stop.sh"
echo "=================================================="

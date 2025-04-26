#!/bin/bash

# Update configuration script for Manufacturing Emulator System
# This script updates the configuration to allow external access and creates a new zip file

echo "Updating configuration to allow external access..."

# Create a temporary directory
mkdir -p temp_update

# Copy the manufacturing emulator without the venv folder
cp -r manufacturing_emulator temp_update/

# Run the configuration update script
cd temp_update/manufacturing_emulator
python3 config_update.py

# Create a new zip file
cd ../..
zip -r manufacturing_emulator_external_access.zip temp_update/manufacturing_emulator

# Clean up
rm -rf temp_update

echo "Configuration updated and new zip file created: manufacturing_emulator_external_access.zip"
echo "This version is configured to listen on all network interfaces (0.0.0.0) instead of just localhost."
echo "You can now access the system using your server's IP address or hostname."

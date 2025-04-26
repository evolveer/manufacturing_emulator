#!/usr/bin/env python3
"""
Configuration update script for Manufacturing Emulator System
This script updates the configuration to allow external access to the system
"""
import os
import yaml
import sys

def update_config():
    """Update the configuration to allow external access"""
    config_path = 'config.yaml'
    
    # Check if config file exists
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found.")
        return False
    
    try:
        # Load the configuration
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        # Update host settings to listen on all interfaces
        if 'erp' in config:
            config['erp']['host'] = '0.0.0.0'
        if 'mes' in config:
            config['mes']['host'] = '0.0.0.0'
        if 'pcs' in config:
            config['pcs']['host'] = '0.0.0.0'
        if 'interface' in config:
            config['interface']['host'] = '0.0.0.0'
        
        # Save the updated configuration
        with open(config_path, 'w') as file:
            yaml.dump(config, file, default_flow_style=False)
        
        print("Configuration updated successfully. The system will now listen on all network interfaces.")
        print("You can access the system using your server's IP address or hostname.")
        return True
    
    except Exception as e:
        print(f"Error updating configuration: {str(e)}")
        return False

if __name__ == "__main__":
    update_config()

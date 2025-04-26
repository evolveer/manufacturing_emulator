"""
ERP Emulator - Main Module
Entry point for the ERP emulator
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

# Import ERP modules
from api import run_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'erp', 'erp.log'))
    ]
)

logger = logging.getLogger('erp_emulator')

def main():
    """Main entry point for the ERP emulator"""
    logger.info("Starting ERP Emulator...")
    try:
        run_app()
    except Exception as e:
        logger.error(f"Error starting ERP Emulator: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

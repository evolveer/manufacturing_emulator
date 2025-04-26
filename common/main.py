"""
PCS Emulator - Main Module
Entry point for the PCS emulator
"""
import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

# Import PCS modules
from api import run_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_root, 'common', 'common.log'))
    ]
)

logger = logging.getLogger('pcs_emulator')

def main():
    """Main entry point for the PCS emulator"""
    logger.info("Starting Common Emulator...")
    try:
        run_app()
    except Exception as e:
        logger.error(f"Error starting Common Emulator: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

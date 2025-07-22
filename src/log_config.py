import logging
import os
import sys

def setup_logging():
    APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".antidtfplus")
    os.makedirs(APP_DATA_DIR, exist_ok=True)

    log_filename = "service.log" if "auto_service.py" in sys.argv[0] else "app.log"
    log_file_path = os.path.join(APP_DATA_DIR, log_filename)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True
    )
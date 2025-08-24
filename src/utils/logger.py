import logging
import os
import sys

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(instance_id, level=logging.INFO):
    logger = logging.getLogger(f"Bot_{instance_id}")
    logger.setLevel(level)
    logger.propagate = False
    if logger.hasHandlers():
        return logger

    log_file = os.path.join(LOG_DIR, f"bot_{instance_id}.log")
    file_handler = logging.FileHandler(log_file, mode='w')
    console_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(f'%(asctime)s - [Bot {instance_id}] - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

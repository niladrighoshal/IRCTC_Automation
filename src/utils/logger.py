import logging
import os
from src.config import LOG_DIR

# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(instance_id, level=logging.INFO):
    """
    Sets up a dedicated logger for a specific bot instance.

    This ensures that logs from different concurrent bots are written to separate files
    and can be distinguished in the console output.

    Args:
        instance_id (int or str): A unique identifier for the logger (e.g., bot ID).
        level (int): The logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(f"Bot_{instance_id}")
    logger.setLevel(level)

    # Prevent logs from propagating to the root logger, which might have other handlers
    logger.propagate = False

    # Return existing logger if it's already configured
    if logger.hasHandlers():
        return logger

    # --- File Handler ---
    # Writes logs to a file like 'logs/bot_1.log'
    log_file = os.path.join(LOG_DIR, f"bot_{instance_id}.log")
    file_handler = logging.FileHandler(log_file, mode='w') # 'w' to overwrite log on each run
    file_handler.setLevel(level)

    # --- Console Handler ---
    # Writes logs to the standard console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # --- Formatter ---
    # Defines the log message format
    formatter = logging.Formatter(
        f'%(asctime)s - [Bot {instance_id}] - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

if __name__ == '__main__':
    # Example of how to use the logger
    print(f"Log files will be saved in: {os.path.abspath(LOG_DIR)}")

    # Get logger for bot instance 1
    logger1 = setup_logger(1)
    logger1.info("Logger for bot 1 initialized.")
    logger1.info("This is an informational message.")
    logger1.warning("This is a warning message.")

    # Get logger for bot instance 2
    logger2 = setup_logger(2)
    logger2.info("Logger for bot 2 initialized.")
    logger2.debug("This is a debug message (it will not appear with default INFO level).")

    logger1.error("This is an error message for bot 1.")

    print("\nCheck the 'logs' directory for bot_1.log and bot_2.log files.")

import logging
from logging.handlers import RotatingFileHandler
import sys
from utils.constants import LOG_DIR

def setup_logger():
    logger = logging.getLogger("TailChat")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (Rotating, max 5MB, keep 3 backups)
    log_file = LOG_DIR / "app.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

import os
import logging
from logging.handlers import RotatingFileHandler

def get_logger(name, log_level=logging.INFO, log_dir=None):
    """
    Create and configure a logger
    
    Args:
        name (str): Logger name
        log_level (int): Log level (default: INFO)
        log_dir (str, optional): Directory for log files
    
    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    
    # Don't configure the logger multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log directory is specified
    if log_dir:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f"{name.replace('.', '_')}.log")
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# logger.py
# VERSION: 3.0 - FIXED LOGGING + MULTIPROCESSING
# CHANGES: Fixed init_logging return, proper multiprocessing support

import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config import AppConstants
import multiprocessing


def init_logging():
    """
    Initialize logging system with multiprocessing support.
    
    Returns:
        logging.Logger: Root logger instance
    """
    os.makedirs(AppConstants.log_dir, exist_ok=True)
    
    # Determine log file based on process
    process_name = multiprocessing.current_process().name
    pid = os.getpid()
    
    if process_name == 'MainProcess':
        log_filename = 'main.log'
    elif 'Process' in process_name or 'Collector' in process_name:
        # Extract bookmaker name from process name
        # e.g., "BalkanBet-Process" -> "balkanbet"
        bookmaker = process_name.replace('-Process', '').replace('Collector-', '').lower()
        log_filename = f'{bookmaker}_{pid}.log'
    else:
        log_filename = f'{process_name.lower()}_{pid}.log'
    
    log_file = os.path.join(AppConstants.log_dir, log_filename)
    
    # Create handlers
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=AppConstants.log_max_bytes,
        backupCount=AppConstants.log_backup_count,
        encoding='utf-8'  # IMPORTANT for Serbian characters
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Formatting
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '[%(name)s] %(message)s'
    )
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if AppConstants.debug else logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Initial log message
    logger = AviatorLogger.get_logger("System")
    logger.info("=" * 60)
    logger.info(f"Logging initialized - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Process: {process_name} (PID: {pid})")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Debug mode: {AppConstants.debug}")
    logger.info("=" * 60)
    
    return root_logger  # ✅FIXED: Now returns logger


class AviatorLogger:
    """Custom logger wrapper with caching."""
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str):
        """Get or create logger instance."""
        if name not in cls._loggers:
            cls._loggers[name] = cls(name)
        return cls._loggers[name]
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def debug(self, message, *args, **kwargs):
        """Log debug message (only if debug mode enabled)."""
        if AppConstants.debug:
            self.logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        """Log info message."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Log error message."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)
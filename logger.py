# logger.py
"""
Aviator Logging System
Version: 3.0 - FIXED
Critical fix: init_logging() now returns logger object
"""

import logging
import logging.handlers
import multiprocessing
from pathlib import Path
from typing import Optional
import sys
import os
from config import app_config


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        """Format log record with colors if outputting to terminal"""
        # Only use colors if outputting to terminal
        if hasattr(sys.stdout, 'isatty') and sys.stdout.isatty():
            record.levelname = (
                f"{self.COLORS.get(record.levelname, '')}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


class AviatorLogger:
    """Central logging manager for Aviator project"""
    
    _loggers = {}
    _initialized = False
    _root_logger = None
    
    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """
        Get or create a logger instance
        
        Args:
            name: Logger name (defaults to caller's module)
            
        Returns:
            Configured logger instance
        """
        if not cls._initialized:
            init_logging()
        
        if name is None:
            # Get caller's module name
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back:
                name = frame.f_back.f_globals.get('__name__', 'Unknown')
        
        # Truncate long names for better formatting
        if len(name) > 20:
            name = f"{name[:17]}..."
        
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        
        return cls._loggers[name]
    
    @classmethod
    def get_process_logger(cls, process_name: str) -> logging.Logger:
        """Get logger for multiprocessing context"""
        pid = multiprocessing.current_process().pid
        logger_name = f"{process_name}_{pid}"
        return cls.get_logger(logger_name)


def init_logging(
    debug: bool = None,
    log_dir: Path = None,
    console_output: bool = True
) -> logging.Logger:
    """
    Initialize the logging system
    
    CRITICAL FIX v3.0: This function now returns the root logger
    
    Args:
        debug: Enable debug logging (defaults to app_config.debug)
        log_dir: Directory for log files (defaults to app_config.logs_dir)
        console_output: Enable console output
        
    Returns:
        logging.Logger: The configured root logger
    """
    if AviatorLogger._initialized:
        return AviatorLogger._root_logger
    
    # Use defaults from config if not specified
    if debug is None:
        debug = app_config.debug
    if log_dir is None:
        log_dir = app_config.logs_dir
    
    # Ensure log directory exists
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Create formatters
    file_formatter = logging.Formatter(
        fmt=app_config.log_format,
        datefmt=app_config.log_date_format
    )
    
    console_formatter = ColoredFormatter(
        fmt=app_config.log_format,
        datefmt=app_config.log_date_format
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'main.log',
        maxBytes=app_config.log_max_bytes,
        backupCount=app_config.log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Error file handler (always active)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'error.log',
        maxBytes=app_config.log_max_bytes,
        backupCount=app_config.log_backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Set up process-specific log files for multiprocessing
    if hasattr(multiprocessing, 'current_process'):
        process = multiprocessing.current_process()
        if process.name != 'MainProcess':
            process_handler = logging.handlers.RotatingFileHandler(
                filename=log_dir / f'{process.name.lower()}_{process.pid}.log',
                maxBytes=app_config.log_max_bytes,
                backupCount=2,
                encoding='utf-8'
            )
            process_handler.setLevel(logging.DEBUG if debug else logging.INFO)
            process_handler.setFormatter(file_formatter)
            root_logger.addHandler(process_handler)
    
    # Mark as initialized
    AviatorLogger._initialized = True
    AviatorLogger._root_logger = root_logger
    
    # Log initialization
    logger = AviatorLogger.get_logger("System")
    logger.info("="*60)
    logger.info(f"Logging initialized - Debug: {debug}")
    logger.info(f"Log directory: {log_dir}")
    logger.info(f"Process: {multiprocessing.current_process().name} "
                f"(PID: {os.getpid()})")
    logger.info("="*60)
    
    # CRITICAL FIX: Return the root logger
    return root_logger


def setup_process_logging(process_name: str) -> logging.Logger:
    """
    Setup logging for a child process in multiprocessing
    
    Args:
        process_name: Name of the process
        
    Returns:
        Logger configured for this process
    """
    # Re-initialize logging in child process
    init_logging()
    
    # Get process-specific logger
    logger = AviatorLogger.get_process_logger(process_name)
    logger.info(f"Process logging initialized for {process_name}")
    
    return logger


def log_exception(logger: logging.Logger, exc: Exception, context: str = None):
    """
    Log an exception with full traceback
    
    Args:
        logger: Logger instance
        exc: Exception to log
        context: Additional context about where exception occurred
    """
    import traceback
    
    error_msg = f"Exception in {context}: {str(exc)}" if context else str(exc)
    logger.error(error_msg)
    logger.debug("Full traceback:\n" + traceback.format_exc())


def get_file_handler_path(logger_name: str = None) -> Path:
    """
    Get the path to a logger's file handler
    
    Args:
        logger_name: Name of logger (None for root)
        
    Returns:
        Path to log file or None if no file handler
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return Path(handler.baseFilename)
    
    return None


def rotate_logs():
    """Force rotation of all log files"""
    root_logger = logging.getLogger()
    
    for handler in root_logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.doRollover()
    
    logger = AviatorLogger.get_logger("System")
    logger.info("Log files rotated")


# Convenience functions for quick logging
def debug(msg: str, *args, **kwargs):
    """Quick debug logging"""
    AviatorLogger.get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Quick info logging"""
    AviatorLogger.get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Quick warning logging"""
    AviatorLogger.get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Quick error logging"""
    AviatorLogger.get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Quick critical logging"""
    AviatorLogger.get_logger().critical(msg, *args, **kwargs)


# Export main components
__all__ = [
    'AviatorLogger',
    'init_logging',
    'setup_process_logging',
    'log_exception',
    'get_file_handler_path',
    'rotate_logs',
    'debug',
    'info',
    'warning',
    'error',
    'critical'
]
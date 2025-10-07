# logger.py
# VERSION: 5.0 - Fixed for new config system
# Centralized logging system

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class AviatorLogger:
    """
    Centralized logger for Aviator project.
    
    Features:
    - Rotating file handlers (10MB per file, 5 backups)
    - Console output with color coding
    - Separate loggers per module
    - Thread-safe
    """
    
    _initialized = False
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger instance.
        
        Args:
            name: Logger name (usually module name)
        
        Returns:
            Configured logger
        """
        # Initialize on first call
        if not cls._initialized:
            init_logging()
        
        # Return existing logger if available
        if name in cls._loggers:
            return cls._loggers[name]
        
        # Create new logger
        logger = logging.getLogger(name)
        cls._loggers[name] = logger
        
        return logger


def init_logging(
    log_level: str = "INFO",
    log_to_console: bool = True,
    log_to_file: bool = True
) -> None:
    """
    Initialize logging system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Enable console output
        log_to_file: Enable file output
    """
    
    if AviatorLogger._initialized:
        return
    
    # Import config here to avoid circular imports
    try:
        from config import config
        log_dir = config.paths.logs_dir
        log_format = config.logging.format
        date_format = config.logging.date_format
        max_bytes = config.logging.max_bytes
        backup_count = config.logging.backup_count
    except Exception as e:
        # Fallback to defaults if config not available
        log_dir = Path("logs")
        log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        max_bytes = 10 * 1024 * 1024  # 10MB
        backup_count = 5
    
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler (main log)
    if log_to_file:
        main_log_file = log_dir / "main.log"
        file_handler = RotatingFileHandler(
            main_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Error log (errors only)
        error_log_file = log_dir / "error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    AviatorLogger._initialized = True
    
    # Log initialization
    logger = logging.getLogger("Logger")
    logger.info("="*60)
    logger.info("Logging system initialized")
    logger.info(f"Log directory: {log_dir}")
    logger.info(f"Log level: {log_level}")
    logger.info("="*60)


def get_module_logger(
    module_name: str,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Get logger for specific module with optional separate log file.
    
    Args:
        module_name: Name of the module
        log_file: Optional separate log file name (e.g., 'betting_agent.log')
    
    Returns:
        Configured logger
    """
    # Initialize if not done
    if not AviatorLogger._initialized:
        init_logging()
    
    # Get or create logger
    logger = logging.getLogger(module_name)
    
    # Add separate file handler if requested
    if log_file and not any(
        isinstance(h, RotatingFileHandler) and log_file in str(h.baseFilename)
        for h in logger.handlers
    ):
        try:
            from config import config
            log_dir = config.paths.logs_dir
            max_bytes = config.logging.max_bytes
            backup_count = config.logging.backup_count
            log_format = config.logging.format
            date_format = config.logging.date_format
        except:
            log_dir = Path("logs")
            max_bytes = 10 * 1024 * 1024
            backup_count = 5
            log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
            date_format = "%Y-%m-%d %H:%M:%S"
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        file_handler = RotatingFileHandler(
            log_dir / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    
    return logger


# Convenience functions
def debug(msg: str, logger_name: str = "Main"):
    """Log debug message."""
    AviatorLogger.get_logger(logger_name).debug(msg)


def info(msg: str, logger_name: str = "Main"):
    """Log info message."""
    AviatorLogger.get_logger(logger_name).info(msg)


def warning(msg: str, logger_name: str = "Main"):
    """Log warning message."""
    AviatorLogger.get_logger(logger_name).warning(msg)


def error(msg: str, logger_name: str = "Main", exc_info: bool = False):
    """Log error message."""
    AviatorLogger.get_logger(logger_name).error(msg, exc_info=exc_info)


def critical(msg: str, logger_name: str = "Main", exc_info: bool = False):
    """Log critical message."""
    AviatorLogger.get_logger(logger_name).critical(msg, exc_info=exc_info)


# Test function
def test_logging():
    """Test logging functionality."""
    print("\n" + "="*60)
    print("TESTING LOGGING SYSTEM")
    print("="*60)
    
    # Initialize
    init_logging(log_level="DEBUG")
    
    # Create test logger
    logger = AviatorLogger.get_logger("TestModule")
    
    # Test all levels
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
    
    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.error("Caught exception:", exc_info=True)
    
    print("\n" + "="*60)
    print("Check logs/ directory for log files")
    print("="*60)


if __name__ == "__main__":
    test_logging()
import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from typing import Optional

default_log_level = logging.INFO  # Default log level if not specified

class LoggerWrapper:
    def __init__(self):
        self._loggers = {}

    def get_logger(self, name: str, log_to_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False  # Prevent duplicate logs

        # Console handler
        console_handler = StreamHandler()
        console_handler.setFormatter(self._get_default_formatter())
        logger.addHandler(console_handler)

        # Optional file handler
        if log_to_file:
            file_handler = RotatingFileHandler(log_to_file, maxBytes=5 * 1024 * 1024, backupCount=3)
            file_handler.setFormatter(self._get_default_formatter())
            logger.addHandler(file_handler)

        self._loggers[name] = logger
        return logger

    @staticmethod
    def _get_default_formatter() -> logging.Formatter:
        return logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


# Singleton instance of LoggerWrapper
_logger_wrapper = LoggerWrapper()

def get_logger(name: str, log_to_file: Optional[str] = None, level: int = default_log_level) -> logging.Logger:
    return _logger_wrapper.get_logger(name, log_to_file, level)
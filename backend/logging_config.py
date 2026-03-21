"""
Octant AI — Master Logging Configuration

Dictates unified multi-formatter routing for console vs production JSON scraping.
Allows injection of context via standard Python logging mechanics.
"""

import os
import json
import logging
import sys

class JSONFormatter(logging.Formatter):
    """Outputs rigid JSON for ELK/Datadog ingests during Docker execution."""
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        }
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

class ConsoleFormatter(logging.Formatter):
    """Outputs human readable format with contextual injection for development."""
    def format(self, record):
        session_str = f" [{record.session_id}]" if hasattr(record, "session_id") else ""
        return f"{self.formatTime(record, self.datefmt)} | {record.levelname:<8} | {record.module}{session_str} : {record.getMessage()}"

def get_logger(name: str) -> logging.Logger:
    """Retrieves the pre-configured logging interface."""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if imported heavily
    if logger.handlers:
        return logger
        
    log_level_str = os.environ.get("LOG_LEVEL", "DEBUG").upper()
    level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    
    # Check if standard production mode
    log_format = os.environ.get("LOG_FORMAT", "pretty").lower()
    if log_format == "json":
        handler.setFormatter(JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ"))
    else:
        handler.setFormatter(ConsoleFormatter(datefmt="%Y-%m-%d %H:%M:%S"))
        
    logger.addHandler(handler)
    logger.propagate = False
    return logger

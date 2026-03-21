"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import os
import json
import logging
import sys

class JSONFormatter(logging.Formatter):
    """outputs rigid json for elk/datadog ingests during docker execution lol"""
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
    """outputs human readable format with contextual injection for development lol"""
    def format(self, record):
        session_str = f" [{record.session_id}]" if hasattr(record, "session_id") else ""
        return f"{self.formatTime(record, self.datefmt)} | {record.levelname:<8} | {record.module}{session_str} : {record.getMessage()}"

def get_logger(name: str) -> logging.Logger:
    """retrieves the pre-configured logging interface lol"""
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

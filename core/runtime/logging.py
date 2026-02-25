import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

class JsonFormatter(logging.Formatter):
    """Custom formatter to output log records as JSON."""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Merge extra fields if present
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
            
        return json.dumps(log_entry)

def setup_logging(level=logging.INFO):
    """Configures GemForge logging with JSON file output and clean console output."""
    root_logger = logging.getLogger("gemforge")
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. Console Handler (Pretty-printed)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "   %(levelname)s [%(name)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. File Handler (JSON)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "gemforge.json.log")
    file_handler.setLevel(level)
    file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(file_handler)

    return root_logger

# Singleton-ish access
logger = logging.getLogger("gemforge")

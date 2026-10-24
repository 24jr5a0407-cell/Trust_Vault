import logging
import sys
from config import LOG_LEVEL

def setup_logger(name: str = "trustvault") -> logging.Logger:
    """Configures a standardized structured logger for the Trust Vault application."""
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(level)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger

# Global app logger
logger = setup_logger("trustvault")

"""
Structured logging configuration for NivasAI
"""

import logging
import logging.config
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import structlog
from pythonjsonlogger import jsonlogger

from app.config import settings


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging"""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add service info
        log_record['service'] = settings.APP_NAME
        log_record['environment'] = 'development' if settings.DEBUG else 'production'
        
        # Add log level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Create colored format
        formatter = logging.Formatter(
            f"{color}%(asctime)s - %(name)s - %(levelname)s{reset} - %(message)s"
        )
        
        return formatter.format(record)


def setup_logging():
    """Setup logging configuration"""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter(
                JSONFormatter()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
                "format": "%(timestamp)s %(level)s %(name)s %(message)s"
            },
            "console": {
                "()": ColoredConsoleFormatter
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "console" if settings.DEBUG else "json",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.LOG_LEVEL,
                "formatter": "json",
                "filename": logs_dir / "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": logs_dir / "error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file", "error_file"]
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "google.cloud": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            },
            "firebase_admin": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get structured logger"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class for adding logging to classes"""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for class"""
        return get_logger(self.__class__.__name__)


class RequestLogger:
    """Request logging middleware helper"""
    
    def __init__(self):
        self.logger = get_logger("request")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log HTTP request"""
        self.logger.info(
            "HTTP request",
            method=method,
            path=path,
            status_code=status_code,
            response_time=response_time,
            user_id=user_id,
            request_id=request_id
        )
    
    def log_error(
        self,
        method: str,
        path: str,
        error: Exception,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """Log HTTP error"""
        self.logger.error(
            "HTTP request error",
            method=method,
            path=path,
            error=str(error),
            error_type=type(error).__name__,
            user_id=user_id,
            request_id=request_id
        )


class BusinessLogger:
    """Business event logging"""
    
    def __init__(self):
        self.logger = get_logger("business")
    
    def log_complaint_created(
        self,
        complaint_id: str,
        user_id: str,
        category: str,
        severity: str,
        ward_id: str
    ):
        """Log complaint creation"""
        self.logger.info(
            "Complaint created",
            event_type="complaint_created",
            complaint_id=complaint_id,
            user_id=user_id,
            category=category,
            severity=severity,
            ward_id=ward_id
        )
    
    def log_complaint_classified(
        self,
        complaint_id: str,
        category: str,
        severity: str,
        confidence: float
    ):
        """Log complaint classification"""
        self.logger.info(
            "Complaint classified",
            event_type="complaint_classified",
            complaint_id=complaint_id,
            category=category,
            severity=severity,
            confidence=confidence
        )
    
    def log_complaint_routed(
        self,
        complaint_id: str,
        officer_id: str,
        department: str
    ):
        """Log complaint routing"""
        self.logger.info(
            "Complaint routed",
            event_type="complaint_routed",
            complaint_id=complaint_id,
            officer_id=officer_id,
            department=department
        )
    
    def log_housing_match(
        self,
        user_id: str,
        family_profile_id: str,
        matches_count: int,
        top_score: float
    ):
        """Log housing matching"""
        self.logger.info(
            "Housing match completed",
            event_type="housing_match",
            user_id=user_id,
            family_profile_id=family_profile_id,
            matches_count=matches_count,
            top_score=top_score
        )
    
    def log_ward_analysis(
        self,
        ward_id: str,
        overall_score: float,
        top_priority: str
    ):
        """Log ward analysis"""
        self.logger.info(
            "Ward analysis completed",
            event_type="ward_analysis",
            ward_id=ward_id,
            overall_score=overall_score,
            top_priority=top_priority
        )
    
    def log_whatsapp_message(
        self,
        phone_number: str,
        intent: str,
        message_type: str
    ):
        """Log WhatsApp message"""
        self.logger.info(
            "WhatsApp message processed",
            event_type="whatsapp_message",
            phone_number=phone_number,
            intent=intent,
            message_type=message_type
        )


# Global loggers
request_logger = RequestLogger()
business_logger = BusinessLogger()

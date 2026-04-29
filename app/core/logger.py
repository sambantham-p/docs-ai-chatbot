import json
import logging
import logging.handlers
import os
import time
from logging.config import dictConfig
from pathlib import Path
from app.core.logging_config import (
    LOG_FILE_NAME,
    ERROR_FILE_NAME,
    FILE_PERMISSIONS,
    get_log_level,
    get_retention_days,
    use_json_logs, DEFAULT_RETENTION_DAYS,
)

logger = logging.getLogger(__name__)

class StructuredJsonFormatter(logging.Formatter):

    """Formats log records into structured JSON for machine-readable logging."""
    def format(self, record: logging.LogRecord) -> str:
        ts = record.created
        utc = time.gmtime(ts)
        millis = int((ts - int(ts)) * 1000)

        timestamp = "{}.{:03d}Z".format(
            time.strftime("%Y-%m-%dT%H:%M:%S", utc),
            millis,
        )
        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=False)


# HELPERS

"""Resolve project root from env or fallback to repository structure."""
def _project_root() -> Path:
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


"""Resolve and create log directory from env or fallback to project logs folder."""
def _resolve_log_dir(project_root: Path) -> Path:
    env_dir = os.getenv("LOG_DIR")
    if env_dir:
        try:
            candidate = Path(env_dir).expanduser().resolve()
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception as exc:
            logger.warning("Invalid LOG_DIR, falling back to default: %s", exc)
    fallback = (project_root / "logs").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


"""Apply secure file permissions to log files if they exist."""
def _apply_file_permissions(*paths: Path) -> None:
    for path in paths:
        try:
            if path.exists():
                path.chmod(FILE_PERMISSIONS)
        except OSError:
            logger.debug("Failed to set permissions for %s", path)


"""Ensure log files exist before applying permissions."""
def _ensure_files_exist(*paths: Path) -> None:
    for path in paths:
        try:
            path.touch(exist_ok=True)
        except OSError:
            logger.debug("Failed to create file %s", path)


"""Clear existing root handlers to prevent duplicate logging."""
def _clear_root_handlers() -> None:
    root = logging.getLogger()
    for handler in root.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
    root.handlers.clear()


def setup_logging() -> None:
    logging.Formatter.converter = time.gmtime
    log_level = get_log_level()
    retention_days = get_retention_days()
    use_json = use_json_logs()
    project_root = _project_root()
    log_dir = _resolve_log_dir(project_root)
    log_file = log_dir / LOG_FILE_NAME
    error_file = log_dir / ERROR_FILE_NAME
    formatter = "json" if use_json else "text"
    _clear_root_handlers()
    rotating_base = {
        "class": "logging.handlers.TimedRotatingFileHandler",
        "formatter": formatter,
        "when": "midnight",
        "interval": 1,
        "backupCount": retention_days,
        "encoding": "utf-8",
        "delay": True,
        "utc": True,
    }
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "text": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%SZ",
            },
            "json": {
                "()": StructuredJsonFormatter,
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter,
                "level": log_level,
                "stream": "ext://sys.stdout",
            },
            "app_file": {
                **rotating_base,
                "level": log_level,
                "filename": str(log_file),
            },
            "error_file": {
                **rotating_base,
                "level": "ERROR",
                "filename": str(error_file),
            },
        },

        "root": {
            "level": log_level,
            "handlers": ["console", "app_file", "error_file"],
        },

        "loggers": {
            "uvicorn": {
                "level": log_level,
                "handlers": ["console", "app_file", "error_file"],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": log_level,
                "handlers": ["console", "app_file", "error_file"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "app_file"],
                "propagate": False,
            },
        },
    }

    dictConfig(config)
    # Ensure files exist BEFORE chmod
    _ensure_files_exist(log_file, error_file)
    _apply_file_permissions(log_file, error_file)
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging initialised | level=%s | format=%s | dir=%s | retention=%d days",
        log_level, formatter, log_dir, retention_days,
    )
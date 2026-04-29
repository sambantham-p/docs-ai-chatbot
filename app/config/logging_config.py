import os

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_RETENTION_DAYS = 14
LOG_FILE_NAME = "app.log"
ERROR_FILE_NAME = "error.log"
FILE_PERMISSIONS = 0o640

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

def get_log_level() -> str:
    raw = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    return raw if raw in _VALID_LOG_LEVELS else DEFAULT_LOG_LEVEL

def get_retention_days() -> int:
    raw = os.getenv("LOG_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
    try:
        value = int(raw)
        return value if value > 0 else DEFAULT_RETENTION_DAYS
    except Exception:
        return DEFAULT_RETENTION_DAYS

def use_json_logs() -> bool:
    return os.getenv("LOG_JSON", "false").lower() in ("1", "true", "yes")
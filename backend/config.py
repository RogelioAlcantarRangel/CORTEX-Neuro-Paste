import json
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "ws_host": "localhost",
    "ws_port": 8989,
    "transform_rules": ["uppercase"],
    "log_level": "INFO",
    "log_file": "backend/backend.log",
}


CONFIG_PATH = Path(__file__).with_name("config.json")


def _coerce_host(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_CONFIG["ws_host"]


def _coerce_port(value: Any) -> int:
    if isinstance(value, int) and 1 <= value <= 65535:
        return value
    if isinstance(value, str) and value.isdigit():
        port = int(value)
        if 1 <= port <= 65535:
            return port
    return DEFAULT_CONFIG["ws_port"]


def _coerce_rules(value: Any) -> list[str]:
    if not isinstance(value, list):
        return list(DEFAULT_CONFIG["transform_rules"])
    valid_rules = [rule for rule in value if isinstance(rule, str) and rule.strip()]
    return valid_rules if valid_rules else list(DEFAULT_CONFIG["transform_rules"])


def _coerce_log_level(value: Any) -> str:
    valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    if isinstance(value, str) and value.strip().upper() in valid_levels:
        return value.strip().upper()
    return DEFAULT_CONFIG["log_level"]


def _coerce_log_file(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_CONFIG["log_file"]


def load_config() -> Dict[str, Any]:
    """Carga configuración de backend/config.json con fallback seguro a defaults."""
    config = dict(DEFAULT_CONFIG)

    if not CONFIG_PATH.exists():
        return config

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return config

    if not isinstance(raw, dict):
        return config

    config["ws_host"] = _coerce_host(raw.get("ws_host"))
    config["ws_port"] = _coerce_port(raw.get("ws_port"))
    config["transform_rules"] = _coerce_rules(raw.get("transform_rules"))
    config["log_level"] = _coerce_log_level(raw.get("log_level"))
    config["log_file"] = _coerce_log_file(raw.get("log_file"))
    return config

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "ws_host": "localhost",
    "ws_port": 8989,
    "transform_rules": ["uppercase"],
    "token_rotation_seconds": 86400,
    "auth_tokens": [
        {
            "client_token": "dev-token",
            "expires_at": "2099-01-01T00:00:00+00:00",
        }
    ],
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


def _coerce_rotation_seconds(value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdigit():
        seconds = int(value)
        if seconds > 0:
            return seconds
    return DEFAULT_CONFIG["token_rotation_seconds"]


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _coerce_auth_tokens(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return list(DEFAULT_CONFIG["auth_tokens"])

    now = datetime.now(timezone.utc)
    tokens: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        token = item.get("client_token")
        expires_at_raw = item.get("expires_at")
        expires_at = _parse_iso_datetime(expires_at_raw)
        if not isinstance(token, str) or not token.strip() or expires_at is None:
            continue
        token = token.strip()
        if expires_at <= now:
            continue
        tokens.append(
            {
                "client_token": token,
                "expires_at": expires_at.isoformat(),
            }
        )

    return tokens if tokens else list(DEFAULT_CONFIG["auth_tokens"])


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
    config["token_rotation_seconds"] = _coerce_rotation_seconds(raw.get("token_rotation_seconds"))
    config["auth_tokens"] = _coerce_auth_tokens(raw.get("auth_tokens"))
    return config

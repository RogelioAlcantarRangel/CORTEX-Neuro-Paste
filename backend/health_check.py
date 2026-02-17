import argparse
import base64
import json
import socket
import sys

from config import load_config


def check_port(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"Puerto {host}:{port} accesible"
    except OSError as exc:
        return False, f"No se pudo conectar al puerto {host}:{port}: {exc}"


def check_cortex_handshake(host: str, port: int, timeout: float) -> tuple[bool, str]:
    key = base64.b64encode(b"cortex-health-check").decode("ascii")
    request = (
        "GET /cortex HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(request.encode("utf-8"))
            response = sock.recv(4096).decode("utf-8", errors="ignore")
    except OSError as exc:
        return False, f"Handshake falló por conexión: {exc}"

    status_line = response.splitlines()[0] if response else ""
    if "101" not in status_line:
        return False, f"Handshake inválido. Status recibido: {status_line or 'sin respuesta'}"

    if "upgrade: websocket" not in response.lower():
        return False, "Handshake inválido: falta cabecera Upgrade: websocket"

    return True, "Handshake WebSocket /cortex correcto (HTTP 101)"


def main() -> int:
    config = load_config()

    parser = argparse.ArgumentParser(description="Health check del backend CORTEX")
    parser.add_argument("--host", default=config["ws_host"])
    parser.add_argument("--port", type=int, default=config["ws_port"])
    parser.add_argument("--timeout", type=float, default=1.5)
    args = parser.parse_args()

    checks = [
        ("port", check_port(args.host, args.port, args.timeout)),
        ("cortex_handshake", check_cortex_handshake(args.host, args.port, args.timeout)),
    ]

    results = {name: {"ok": ok, "detail": detail} for name, (ok, detail) in checks}
    ok = all(item["ok"] for item in results.values())

    print(json.dumps({"ok": ok, "checks": results}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

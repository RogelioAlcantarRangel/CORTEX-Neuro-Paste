import asyncio
import json
import time
import logging
from datetime import datetime, timezone
from itertools import count

from fastapi import FastAPI, WebSocket
import uvicorn
import win32gui

from input_sim import simulate_paste, simulate_select_all, get_active_window_hwnd
from clipboard_mgr import read_clipboard, write_clipboard, process_text
from config import load_config

app = FastAPI()

CONFIG = load_config()
TRANSFORM_RULES = CONFIG["transform_rules"]

# Estado por conexión
window_states = {}
abort_flags = {}
processing_events = {}
connection_cycle_ids = {}
authenticated_connections = {}

_connection_id_counter = count(1)


def _build_token_index(config_tokens):
    token_index = {}
    for item in config_tokens:
        token = item.get("client_token")
        expires_at_raw = item.get("expires_at")
        if not token or not expires_at_raw:
            continue
        try:
            expires_at = datetime.fromisoformat(str(expires_at_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        token_index[token] = expires_at
    return token_index


AUTH_TOKENS = _build_token_index(CONFIG.get("auth_tokens", []))


def log_active_window(step: str):
    """Loggea el título de la ventana activa para debugging de foco."""
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    print(f"{step} - Ventana activa: '{title}' (HWND: {hwnd})")


async def send_event(websocket: WebSocket, payload: dict) -> None:
    """Envía un evento JSON al plugin de forma segura."""
    if websocket.client_state.name != "CONNECTED":
        return
    try:
        await websocket.send_text(json.dumps(payload))
    except Exception as exc:
        print(f"No se pudo enviar evento al plugin: {exc}")


async def send_ack(websocket: WebSocket, action: str, cycle_id=None) -> None:
    await send_event(
        websocket,
        {
            "type": "ack",
            "action": action,
            "cycle_id": cycle_id,
            "ts": time.time(),
        },
    )


async def send_status(websocket: WebSocket, phase: str, cycle_id=None, extra=None) -> None:
    payload = {
        "type": "status",
        "phase": phase,
        "cycle_id": cycle_id,
        "ts": time.time(),
    }
    if extra:
        payload.update(extra)
    await send_event(websocket, payload)


async def send_error(websocket: WebSocket, code: str, message: str, action=None, cycle_id=None) -> None:
    await send_event(
        websocket,
        {
            "type": "error",
            "code": code,
            "message": message,
            "action": action,
            "cycle_id": cycle_id,
            "ts": time.time(),
        },
    )


@app.websocket("/cortex")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = next(_connection_id_counter)
    print(f"WebSocket conectado en /cortex (connection_id={connection_id})")

    abort_flags[websocket] = False
    processing_events[websocket] = asyncio.Event()
    connection_cycle_ids[websocket] = 0
    authenticated_connections[websocket] = False

    await send_status(websocket, "connected", extra={"connection_id": connection_id})

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                await send_error(websocket, "INVALID_JSON", "Payload no es JSON válido")
                continue

            action = message.get("action")
            requested_cycle_id = message.get("cycle_id")

            if action == "hello":
                client_token = message.get("client_token")
                if not isinstance(client_token, str) or not client_token.strip():
                    await send_error(
                        websocket,
                        "INVALID_TOKEN",
                        "client_token faltante o inválido para handshake hello.",
                        action=action,
                    )
                    continue

                expires_at = AUTH_TOKENS.get(client_token.strip())
                if not expires_at:
                    await send_error(
                        websocket,
                        "INVALID_TOKEN",
                        "Token no reconocido.",
                        action=action,
                    )
                    continue

                if expires_at <= datetime.now(timezone.utc):
                    await send_error(
                        websocket,
                        "EXPIRED_TOKEN",
                        "Token expirado. Rotar credencial en plugin/config.json.",
                        action=action,
                    )
                    continue

                authenticated_connections[websocket] = True
                await send_ack(websocket, action)
                await send_status(
                    websocket,
                    "authenticated",
                    extra={
                        "token_expires_at": expires_at.isoformat(),
                        "token_rotation_seconds": CONFIG.get("token_rotation_seconds"),
                    },
                )
                continue

            if not authenticated_connections.get(websocket, False):
                await send_error(
                    websocket,
                    "UNAUTHORIZED",
                    "Handshake requerido. Envía action=hello con client_token válido.",
                    action=action,
                )
                continue

            if action == "paste_cycle":
                connection_cycle_ids[websocket] += 1
                cycle_id = connection_cycle_ids[websocket]

                await send_ack(websocket, action, cycle_id)

                abort_flags[websocket] = False
                processing_events[websocket].clear()

                log_active_window("Paso A - Antes de paste")
                start = time.perf_counter()
                simulate_paste()
                end = time.perf_counter()
                latency_ms = (end - start) * 1000
                log_active_window("Paso A - Después de paste")
                print(f"Paso A latency: {latency_ms:.2f}ms")

                hwnd = get_active_window_hwnd()
                window_states[websocket] = hwnd
                print(f"Paso A - HWND almacenado: {hwnd}")

                await send_status(
                    websocket,
                    "step_a_done",
                    cycle_id,
                    extra={"latency_ms": round(latency_ms, 2), "window_hwnd": hwnd},
                )

                asyncio.create_task(process_clipboard_async(websocket, cycle_id))

            elif action == "replace":
                cycle_id = connection_cycle_ids.get(websocket)
                await send_ack(websocket, action, cycle_id)

                if not cycle_id:
                    await send_error(
                        websocket,
                        "NO_ACTIVE_CYCLE",
                        "No existe un ciclo activo. Ejecuta paste_cycle antes de replace.",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                if requested_cycle_id is not None and requested_cycle_id != cycle_id:
                    await send_error(
                        websocket,
                        "CYCLE_MISMATCH",
                        "cycle_id no coincide con el ciclo activo de la conexión.",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                current_hwnd = get_active_window_hwnd()
                stored_hwnd = window_states.get(websocket)
                if current_hwnd != stored_hwnd:
                    print(f"Ventana cambiada - Actual: {current_hwnd}, Almacenado: {stored_hwnd}")
                    await send_error(
                        websocket,
                        "WINDOW_MISMATCH",
                        "Ventana activa no coincide con la capturada en paste_cycle",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                if abort_flags[websocket]:
                    print("Replace abortado: abort flag activo")
                    await send_error(
                        websocket,
                        "ABORTED",
                        "Replace cancelado por evento abort",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                await processing_events[websocket].wait()

                print(f"Ventana consistente - HWND: {current_hwnd}")

                log_active_window("Paso C - Antes de select_all")
                start = time.perf_counter()
                simulate_select_all()
                log_active_window("Paso C - Después de select_all")
                simulate_paste()
                end = time.perf_counter()
                latency_ms = (end - start) * 1000
                log_active_window("Paso C - Después de paste")
                print(f"Paso C latency: {latency_ms:.2f}ms")

                await send_status(
                    websocket,
                    "replace_done",
                    cycle_id,
                    extra={"latency_ms": round(latency_ms, 2)},
                )

            elif action == "abort":
                cycle_id = connection_cycle_ids.get(websocket)
                await send_ack(websocket, action, cycle_id)

                if not cycle_id:
                    await send_error(
                        websocket,
                        "NO_ACTIVE_CYCLE",
                        "No existe un ciclo activo. Ejecuta paste_cycle antes de abort.",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                if requested_cycle_id is not None and requested_cycle_id != cycle_id:
                    await send_error(
                        websocket,
                        "CYCLE_MISMATCH",
                        "cycle_id no coincide con el ciclo activo de la conexión.",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                abort_flags[websocket] = True
                print("Abort recibido: flag activado")
                await send_status(websocket, "abort_set", cycle_id)

            else:
                print(f"Acción desconocida: {action}")
                await send_error(
                    websocket,
                    "UNKNOWN_ACTION",
                    f"Acción desconocida: {action}",
                    action=action,
                    cycle_id=connection_cycle_ids.get(websocket),
                )
    except Exception as e:
        print(f"Error en WebSocket: {e}")
    finally:
        if websocket in window_states:
            del window_states[websocket]
        if websocket in abort_flags:
            del abort_flags[websocket]
        if websocket in processing_events:
            del processing_events[websocket]
        if websocket in connection_cycle_ids:
            del connection_cycle_ids[websocket]
        if websocket in authenticated_connections:
            del authenticated_connections[websocket]


async def process_clipboard_async(websocket: WebSocket, cycle_id: int):
    """Paso B: Lee, procesa y escribe clipboard de forma asíncrona."""
    try:
        text = read_clipboard()
        processed = process_text(text, rules=TRANSFORM_RULES)
        write_clipboard(processed)
        print("Paso B completado: clipboard procesado y escrito.")
        await send_status(websocket, "step_b_done", cycle_id)
    except Exception as exc:
        await send_error(
            websocket,
            "PROCESSING_FAILED",
            f"Error en procesamiento de clipboard: {exc}",
            action="paste_cycle",
            cycle_id=cycle_id,
        )
    finally:
        if websocket in processing_events:
            processing_events[websocket].set()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    uvicorn.run(app, host=CONFIG["ws_host"], port=CONFIG["ws_port"], log_config=None)

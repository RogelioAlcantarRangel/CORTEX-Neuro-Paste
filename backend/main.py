import asyncio
import json
import logging
import time
from itertools import count
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
import uvicorn
import win32gui

from input_sim import get_active_window_hwnd, simulate_paste, simulate_select_all
from clipboard_mgr import process_text, read_clipboard, write_clipboard
from config import load_config

app = FastAPI()

CONFIG = load_config()
TRANSFORM_RULES = CONFIG["transform_rules"]

ERROR_CODES = {
    "INVALID_JSON": "Payload no es JSON válido",
    "NO_ACTIVE_CYCLE": "No existe un ciclo activo.",
    "CYCLE_MISMATCH": "cycle_id no coincide con el ciclo activo.",
    "WINDOW_MISMATCH": "Ventana activa no coincide con la capturada en paste_cycle.",
    "ABORTED": "Replace cancelado por evento abort.",
    "UNKNOWN_ACTION": "Acción desconocida.",
    "PROCESSING_FAILED": "Error en procesamiento de clipboard.",
}

# Estado por conexión
window_states: dict[WebSocket, int] = {}
abort_flags: dict[WebSocket, bool] = {}
processing_events: dict[WebSocket, asyncio.Event] = {}
connection_cycle_ids: dict[WebSocket, int] = {}
connection_ids: dict[WebSocket, int] = {}

_connection_id_counter = count(1)


def setup_logging() -> None:
    log_level_name = str(CONFIG.get("log_level", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_file = str(CONFIG.get("log_file", "backend/backend.log"))

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def log_event(
    level: int,
    event: str,
    *,
    connection_id: int | None = None,
    cycle_id: int | None = None,
    error_code: str | None = None,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {
        "event": event,
        "connection_id": connection_id,
        "cycle_id": cycle_id,
        "error_code": error_code,
    }
    payload.update(fields)
    logging.log(level, json.dumps(payload, ensure_ascii=False))


def log_active_window(step: str, *, connection_id: int | None = None, cycle_id: int | None = None) -> None:
    """Loggea el título de la ventana activa para debugging de foco."""
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    log_event(
        logging.INFO,
        "active_window",
        connection_id=connection_id,
        cycle_id=cycle_id,
        step=step,
        window_title=title,
        window_hwnd=hwnd,
    )


async def send_event(websocket: WebSocket, payload: dict) -> None:
    """Envía un evento JSON al plugin de forma segura."""
    if websocket.client_state.name != "CONNECTED":
        return
    connection_id = connection_ids.get(websocket)
    cycle_id = payload.get("cycle_id")
    try:
        await websocket.send_text(json.dumps(payload))
        log_event(
            logging.DEBUG,
            "ws_event_sent",
            connection_id=connection_id,
            cycle_id=cycle_id,
            ws_type=payload.get("type"),
        )
    except Exception as exc:
        log_event(
            logging.ERROR,
            "ws_event_send_failed",
            connection_id=connection_id,
            cycle_id=cycle_id,
            error_code="SEND_FAILED",
            detail=str(exc),
        )


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
    connection_id = connection_ids.get(websocket)
    log_event(
        logging.ERROR,
        "ws_error",
        connection_id=connection_id,
        cycle_id=cycle_id,
        error_code=code,
        action=action,
        detail=message,
    )
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
    connection_ids[websocket] = connection_id
    log_event(logging.INFO, "ws_connected", connection_id=connection_id)

    abort_flags[websocket] = False
    processing_events[websocket] = asyncio.Event()
    connection_cycle_ids[websocket] = 0

    await send_status(websocket, "connected", extra={"connection_id": connection_id})

    try:
        while True:
            raw_data = await websocket.receive_text()
            log_event(logging.DEBUG, "ws_message_received", connection_id=connection_id, raw_data=raw_data)
            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                await send_error(websocket, "INVALID_JSON", ERROR_CODES["INVALID_JSON"])
                continue

            action = message.get("action")
            requested_cycle_id = message.get("cycle_id")

            if action == "paste_cycle":
                connection_cycle_ids[websocket] += 1
                cycle_id = connection_cycle_ids[websocket]

                await send_ack(websocket, action, cycle_id)

                abort_flags[websocket] = False
                processing_events[websocket].clear()

                log_active_window("step_a_before_paste", connection_id=connection_id, cycle_id=cycle_id)
                start = time.perf_counter()
                simulate_paste()
                end = time.perf_counter()
                latency_ms = (end - start) * 1000
                log_active_window("step_a_after_paste", connection_id=connection_id, cycle_id=cycle_id)
                log_event(
                    logging.INFO,
                    "step_a_latency",
                    connection_id=connection_id,
                    cycle_id=cycle_id,
                    latency_ms=round(latency_ms, 2),
                )

                hwnd = get_active_window_hwnd()
                window_states[websocket] = hwnd
                log_event(
                    logging.INFO,
                    "step_a_window_stored",
                    connection_id=connection_id,
                    cycle_id=cycle_id,
                    window_hwnd=hwnd,
                )

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
                    log_event(
                        logging.WARNING,
                        "window_mismatch",
                        connection_id=connection_id,
                        cycle_id=cycle_id,
                        error_code="WINDOW_MISMATCH",
                        current_hwnd=current_hwnd,
                        stored_hwnd=stored_hwnd,
                    )
                    await send_error(
                        websocket,
                        "WINDOW_MISMATCH",
                        "Ventana activa no coincide con la capturada en paste_cycle",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                if abort_flags[websocket]:
                    log_event(
                        logging.WARNING,
                        "replace_aborted",
                        connection_id=connection_id,
                        cycle_id=cycle_id,
                        error_code="ABORTED",
                    )
                    await send_error(
                        websocket,
                        "ABORTED",
                        "Replace cancelado por evento abort",
                        action=action,
                        cycle_id=cycle_id,
                    )
                    continue

                await processing_events[websocket].wait()

                log_event(
                    logging.INFO,
                    "window_consistent",
                    connection_id=connection_id,
                    cycle_id=cycle_id,
                    window_hwnd=current_hwnd,
                )

                log_active_window("step_c_before_select_all", connection_id=connection_id, cycle_id=cycle_id)
                start = time.perf_counter()
                simulate_select_all()
                log_active_window("step_c_after_select_all", connection_id=connection_id, cycle_id=cycle_id)
                simulate_paste()
                end = time.perf_counter()
                latency_ms = (end - start) * 1000
                log_active_window("step_c_after_paste", connection_id=connection_id, cycle_id=cycle_id)
                log_event(
                    logging.INFO,
                    "step_c_latency",
                    connection_id=connection_id,
                    cycle_id=cycle_id,
                    latency_ms=round(latency_ms, 2),
                )

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
                log_event(logging.INFO, "abort_set", connection_id=connection_id, cycle_id=cycle_id)
                await send_status(websocket, "abort_set", cycle_id)

            else:
                await send_error(
                    websocket,
                    "UNKNOWN_ACTION",
                    f"Acción desconocida: {action}",
                    action=action,
                    cycle_id=connection_cycle_ids.get(websocket),
                )
    except Exception as exc:
        log_event(logging.ERROR, "ws_connection_error", connection_id=connection_id, detail=str(exc))
    finally:
        for state_map in (window_states, abort_flags, processing_events, connection_cycle_ids, connection_ids):
            if websocket in state_map:
                del state_map[websocket]
        log_event(logging.INFO, "ws_disconnected", connection_id=connection_id)


async def process_clipboard_async(websocket: WebSocket, cycle_id: int):
    """Paso B: Lee, procesa y escribe clipboard de forma asíncrona."""
    connection_id = connection_ids.get(websocket)
    try:
        text = read_clipboard()
        processed = process_text(text, rules=TRANSFORM_RULES)
        write_clipboard(processed)
        log_event(logging.INFO, "step_b_done", connection_id=connection_id, cycle_id=cycle_id)
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
    setup_logging()
    uvicorn.run(app, host=CONFIG["ws_host"], port=CONFIG["ws_port"], log_config=None)

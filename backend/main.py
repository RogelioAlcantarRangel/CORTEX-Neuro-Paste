import asyncio
import json
import time
import logging
from fastapi import FastAPI, WebSocket
import uvicorn
import win32gui

from input_sim import simulate_paste, simulate_select_all, get_active_window_hwnd
from clipboard_mgr import read_clipboard, write_clipboard, process_text

app = FastAPI()

# Diccionario global para almacenar el HWND por conexión WebSocket
window_states = {}

# Diccionario para flags de abort y procesamiento por conexión
abort_flags = {}
processing_events = {}

async def send_status(websocket: WebSocket, status: str, detail: str | None = None) -> None:
    """Envía un estado al cliente WebSocket si la conexión sigue activa."""
    payload = {"status": status}
    if detail is not None:
        payload["detail"] = detail
    try:
        await websocket.send_text(json.dumps(payload))
    except Exception as exc:
        print(f"No se pudo enviar estado '{status}': {exc}")

def log_active_window(step: str):
    """Loggea el título de la ventana activa para debugging de foco."""
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    print(f"{step} - Ventana activa: '{title}' (HWND: {hwnd})")

@app.websocket("/cortex")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket conectado en /cortex")

    # Inicializar flags para esta conexión
    abort_flags[websocket] = False
    processing_events[websocket] = asyncio.Event()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")

            if action == "paste_cycle":
                # Reset flags
                abort_flags[websocket] = False
                processing_events[websocket].clear()
                await send_status(websocket, "accepted", "paste_cycle recibido")

                # Paso A: Trigger inmediato
                log_active_window("Paso A - Antes de paste")
                start = time.perf_counter()
                simulate_paste()
                end = time.perf_counter()
                log_active_window("Paso A - Después de paste")
                print(f"Paso A latency: {(end - start)*1000:.2f}ms")

                # Capturar y almacenar el HWND activo
                hwnd = get_active_window_hwnd()
                window_states[websocket] = hwnd
                print(f"Paso A - HWND almacenado: {hwnd}")

                # Paso B: Procesamiento asíncrono
                asyncio.create_task(process_clipboard_async(websocket))

            elif action == "replace":
                # Verificar consistencia de ventana
                current_hwnd = get_active_window_hwnd()
                stored_hwnd = window_states.get(websocket)
                if current_hwnd != stored_hwnd:
                    print(f"Ventana cambiada - Actual: {current_hwnd}, Almacenado: {stored_hwnd}")
                    await send_status(websocket, "skipped", "ventana cambiada")
                    continue

                # Verificar si abort fue enviado
                if abort_flags[websocket]:
                    print("Replace abortado: abort flag activo")
                    await send_status(websocket, "skipped", "abort activo")
                    continue

                # Esperar a que el procesamiento termine
                try:
                    await asyncio.wait_for(processing_events[websocket].wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    print("Replace abortado: timeout en procesamiento")
                    await send_status(websocket, "timeout", "procesamiento no completado")
                    continue

                print(f"Ventana consistente - HWND: {current_hwnd}")

                # Paso C: Reemplazo condicional
                log_active_window("Paso C - Antes de select_all")
                start = time.perf_counter()
                simulate_select_all()
                log_active_window("Paso C - Después de select_all")
                simulate_paste()
                end = time.perf_counter()
                log_active_window("Paso C - Después de paste")
                print(f"Paso C latency: {(end - start)*1000:.2f}ms")
                await send_status(websocket, "replaced", "replace completado")

            elif action == "abort":
                abort_flags[websocket] = True
                print("Abort recibido: flag activado")
                await send_status(websocket, "aborted", "abort recibido")

            else:
                print(f"Acción desconocida: {action}")
                await send_status(websocket, "unknown", f"accion desconocida: {action}")
    except Exception as e:
        print(f"Error en WebSocket: {e}")
    finally:
        # Limpiar al desconectar
        if websocket in window_states:
            del window_states[websocket]
        if websocket in abort_flags:
            del abort_flags[websocket]
        if websocket in processing_events:
            del processing_events[websocket]

async def process_clipboard_async(websocket: WebSocket):
    """Paso B: Lee, procesa y escribe clipboard de forma asíncrona."""
    try:
        text = read_clipboard()
        processed = process_text(text)
        write_clipboard(processed)
        print("Paso B completado: clipboard procesado y escrito.")
        await send_status(websocket, "processed", "clipboard procesado")
    except Exception as exc:
        print(f"Error en Paso B: {exc}")
        await send_status(websocket, "error", f"procesamiento fallo: {exc}")
    finally:
        # Señalar que el procesamiento terminó
        if websocket in processing_events:
            processing_events[websocket].set()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    uvicorn.run(app, host="localhost", port=8989, log_config=None)

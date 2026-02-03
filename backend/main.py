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
                    continue

                # Verificar si abort fue enviado
                if abort_flags[websocket]:
                    print("Replace abortado: abort flag activo")
                    continue

                # Esperar a que el procesamiento termine
                await processing_events[websocket].wait()

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

            elif action == "abort":
                abort_flags[websocket] = True
                print("Abort recibido: flag activado")

            else:
                print(f"Acción desconocida: {action}")
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
    except Exception as exc:
        print(f"Error en Paso B: {exc}")
    finally:
        # Señalar que el procesamiento terminó
        if websocket in processing_events:
            processing_events[websocket].set()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    uvicorn.run(app, host="localhost", port=8989, log_config=None)

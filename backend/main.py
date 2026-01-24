import asyncio
import json
import time
from fastapi import FastAPI, WebSocket
import uvicorn

from input_sim import simulate_paste, simulate_select_all
from clipboard_mgr import read_clipboard, write_clipboard, process_text

app = FastAPI()

@app.websocket("/cortex")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket conectado en /cortex")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action")
            
            if action == "paste_cycle":
                # Paso A: Trigger inmediato
                start = time.perf_counter()
                simulate_paste()
                end = time.perf_counter()
                print(f"Paso A latency: {(end - start)*1000:.2f}ms")
                
                # Paso B: Procesamiento asíncrono
                asyncio.create_task(process_clipboard_async())
                
            elif action == "replace":
                # Paso C: Reemplazo condicional
                start = time.perf_counter()
                simulate_select_all()
                simulate_paste()
                end = time.perf_counter()
                print(f"Paso C latency: {(end - start)*1000:.2f}ms")
                
            else:
                print(f"Acción desconocida: {action}")
    except Exception as e:
        print(f"Error en WebSocket: {e}")

async def process_clipboard_async():
    """Paso B: Lee, procesa y escribe clipboard de forma asíncrona."""
    text = read_clipboard()
    processed = process_text(text)
    write_clipboard(processed)
    print("Paso B completado: clipboard procesado y escrito.")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8989)
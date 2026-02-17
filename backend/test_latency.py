"""SMOKE TEST DE ENTORNO (manual/e2e).

Este script depende de entorno Windows real, clipboard del sistema,
foco de ventanas y backend/plugin activos. No forma parte de unit tests
ni de CI automatizado; ejecutar manualmente como smoke test.
"""

SMOKE_TEST_SCOPE = "environment_manual"

import asyncio
import json
import logging
import time
from statistics import mean
import websockets

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración del WebSocket
WS_URL = "ws://localhost:8989/cortex"
TEST_MESSAGE = {"action": "paste_cycle"}
NUM_ITERATIONS = 100  # Número de iteraciones para estadísticas

async def measure_rtt():
    """Mide el Round Trip Time (RTT) del WebSocket."""
    latencies = []
    try:
        async with websockets.connect(WS_URL) as websocket:
            logger.info(f"Conectado al WebSocket: {WS_URL}")
            for i in range(NUM_ITERATIONS):
                start_time = time.time()
                # Enviar mensaje
                await websocket.send(json.dumps(TEST_MESSAGE))
                logger.debug(f"Iteración {i+1}: Mensaje enviado: {TEST_MESSAGE}")
                # Recibir respuesta
                response = await websocket.recv()
                end_time = time.time()
                rtt = (end_time - start_time) * 1000  # Convertir a ms
                latencies.append(rtt)
                logger.info(f"Iteración {i+1}: RTT = {rtt:.2f} ms, Respuesta: {response}")
                # Pequeña pausa para evitar sobrecarga
                await asyncio.sleep(0.01)
    except Exception as e:
        logger.error(f"Error durante la medición: {e}")
        return None

    return latencies

def analyze_latencies(latencies):
    """Analiza las latencias y reporta estadísticas."""
    if not latencies:
        logger.error("No se pudieron medir latencias.")
        return

    avg_rtt = mean(latencies)
    min_rtt = min(latencies)
    max_rtt = max(latencies)

    logger.info("=== RESULTADOS DE LATENCIA ===")
    logger.info(f"Promedio RTT: {avg_rtt:.2f} ms")
    logger.info(f"Mínimo RTT: {min_rtt:.2f} ms")
    logger.info(f"Máximo RTT: {max_rtt:.2f} ms")
    logger.info(f"Número de iteraciones: {len(latencies)}")

    if avg_rtt < 10:
        logger.info("✅ RTT promedio < 10ms: Cumple con la Ley del Flanco de Bajada.")
    else:
        logger.warning("❌ RTT promedio >= 10ms: No cumple con la Ley del Flanco de Bajada.")

async def main():
    logger.info("Iniciando testeo de latencia del WebSocket...")
    latencies = await measure_rtt()
    if latencies:
        analyze_latencies(latencies)
    logger.info("Testeo completado.")

if __name__ == "__main__":
    asyncio.run(main())
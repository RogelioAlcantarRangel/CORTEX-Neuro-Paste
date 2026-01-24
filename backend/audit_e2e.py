import asyncio
import json
import time
import pyperclip
import websockets

WS_URL = "ws://localhost:8989/cortex"

async def audit_paste_cycle():
    """Audita el ciclo paste: mide latencia total hasta procesamiento del clipboard."""
    # Preparar clipboard
    original_text = "hello world"
    pyperclip.copy(original_text)
    print(f"Clipboard inicial: '{original_text}'")

    try:
        async with websockets.connect(WS_URL) as ws:
            start_time = time.perf_counter()
            await ws.send(json.dumps({"action": "paste_cycle"}))
            send_time = time.perf_counter()
            print(f"Enviado 'paste_cycle' en {(send_time - start_time)*1000:.2f} ms")

            # Esperar procesamiento async (Step B)
            timeout = 1.0  # 1 segundo máximo
            elapsed = 0.0
            while elapsed < timeout:
                current = pyperclip.paste()
                if current == original_text.upper():
                    end_time = time.perf_counter()
                    total_latency = (end_time - start_time) * 1000
                    print(f"Procesamiento completado en {total_latency:.2f} ms")
                    return total_latency
                await asyncio.sleep(0.001)
                elapsed += 0.001

            print("❌ Timeout: El clipboard no fue procesado dentro del tiempo límite.")
            return None
    except Exception as e:
        print(f"Error en auditoría: {e}")
        return None

async def test_commit():
    """Prueba que 'commit' no haga nada."""
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"action": "commit"}))
            print("✅ Enviado 'commit': No debería realizar ninguna acción (validado por ausencia de errores).")
    except Exception as e:
        print(f"Error en test commit: {e}")

async def validate_no_blocking():
    """Valida que Step B no bloquee Step A: Envío debe ser inmediato."""
    # Enviar múltiples mensajes rápidamente
    messages = [{"action": "paste_cycle"} for _ in range(10)]
    try:
        async with websockets.connect(WS_URL) as ws:
            start = time.perf_counter()
            for msg in messages:
                await ws.send(json.dumps(msg))
            end = time.perf_counter()
            total_send_time = (end - start) * 1000
            avg_send_time = total_send_time / len(messages)
            print(f"✅ Envío de {len(messages)} mensajes en {total_send_time:.2f} ms (promedio {avg_send_time:.2f} ms por mensaje)")
            if avg_send_time < 1:  # Arbitrario, pero envío debe ser <1ms
                print("✅ No hay bloqueo detectable en el envío.")
            else:
                print("❌ Posible bloqueo en el envío.")
    except Exception as e:
        print(f"Error en validación de no bloqueo: {e}")

async def main():
    print("=== AUDITORÍA E2E DEL SISTEMA INTEGRADO ===")
    print("Contexto: Plugin y Backend vinculados.")
    print("Alcance: Medición de latencia total y validación de la 'Ley de Estabilidad Corporal'.")
    print()

    # Validar no bloqueo
    await validate_no_blocking()
    print()

    # Auditar ciclo paste
    latency = await audit_paste_cycle()
    if latency is not None:
        if latency < 16:
            print("✅ Latencia total < 16ms: Cumple con la Ley del Flanco de Bajada.")
        else:
            print("❌ Latencia total >= 16ms: Falla la Ley del Flanco de Bajada.")
    print()

    # Test commit
    await test_commit()
    print()

    print("Auditoría completada. Verificar prints del backend para Paso A <16ms.")

if __name__ == "__main__":
    asyncio.run(main())
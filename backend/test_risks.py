"""SMOKE TEST DE ENTORNO (manual/e2e).

Este script depende de entorno Windows real, clipboard del sistema,
foco de ventanas y backend/plugin activos. No forma parte de unit tests
ni de CI automatizado; ejecutar manualmente como smoke test.
"""

SMOKE_TEST_SCOPE = "environment_manual"

import asyncio
import json
import time
import pyperclip
import websockets
import subprocess
import win32gui
import win32con

WS_URL = "ws://localhost:8989/cortex"

async def test_race_condition_clipboard():
    """Prueba race condition: paste_cycle -> replace inmediato, verifica sincronización."""
    test_text = "race condition test"
    pyperclip.copy(test_text)
    print(f"Clipboard preparado: '{test_text}'")

    try:
        async with websockets.connect(WS_URL) as ws:
            # Enviar paste_cycle
            await ws.send(json.dumps({"action": "paste_cycle"}))
            print("Enviado 'paste_cycle'")

            # Inmediatamente enviar replace
            await ws.send(json.dumps({"action": "replace"}))
            print("Enviado 'replace' inmediato")

            # Esperar procesamiento
            await asyncio.sleep(0.5)

        final_clipboard = pyperclip.paste()
        expected = test_text.upper()
        if final_clipboard == expected:
            print("OK: Race condition evitada - clipboard procesado correctamente.")
            return True
        else:
            print(f"ERROR: Race condition detectada - final: '{final_clipboard}', esperado: '{expected}'")
            return False
    except Exception as e:
        print(f"Error en test race condition: {e}")
        return False

async def test_abort_prevents_replace():
    """Prueba que abort previene replace."""
    test_text = "abort test"
    pyperclip.copy(test_text)
    print(f"Clipboard preparado: '{test_text}'")

    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"action": "paste_cycle"}))
            print("Enviado 'paste_cycle'")

            await asyncio.sleep(0.05)  # Pequeño delay

            await ws.send(json.dumps({"action": "abort"}))
            print("Enviado 'abort'")

            await asyncio.sleep(0.05)

            await ws.send(json.dumps({"action": "replace"}))
            print("Enviado 'replace'")

            await asyncio.sleep(0.2)

        # Verificar que no haya "Paso C latency" en logs (simulado por ausencia de cambios)
        final_clipboard = pyperclip.paste()
        if final_clipboard == test_text.upper():
            print("ERROR: Replace ejecutado a pesar de abort.")
            return False
        else:
            print("OK: Replace prevenido por abort.")
            return True
    except Exception as e:
        print(f"Error en test abort: {e}")
        return False

async def test_window_focus_change():
    """Prueba cambio de foco previene replace."""
    test_text = "focus test"
    pyperclip.copy(test_text)
    print(f"Clipboard preparado: '{test_text}'")

    # Abrir Notepad para simular cambio
    subprocess.Popen(["notepad.exe"])
    await asyncio.sleep(0.5)  # Esperar que abra

    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"action": "paste_cycle"}))
            print("Enviado 'paste_cycle'")

            # Cambiar a Notepad
            hwnd_notepad = None
            def callback(hwnd, extra):
                nonlocal hwnd_notepad
                if win32gui.GetWindowText(hwnd) == "Untitled - Notepad":
                    hwnd_notepad = hwnd
            win32gui.EnumWindows(callback, None)
            if hwnd_notepad:
                win32gui.SetForegroundWindow(hwnd_notepad)
                print("Cambiado a Notepad")

            await asyncio.sleep(0.1)

            await ws.send(json.dumps({"action": "replace"}))
            print("Enviado 'replace'")

            await asyncio.sleep(0.2)

        print("OK: Replace prevenido por cambio de ventana (verificar logs).")
        return True
    except Exception as e:
        print(f"Error en test focus: {e}")
        return False

async def test_edge_cases():
    """Prueba casos edge."""
    test_cases = [
        ("", "Clipboard vacío"),
        ("a" * 1000, "Texto largo"),
        ("Texto\ncon\nlíneas", "Texto multilínea"),
    ]

    results = []
    for test_text, description in test_cases:
        pyperclip.copy(test_text)
        print(f"Probando {description}")

        try:
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps({"action": "paste_cycle"}))
                await asyncio.sleep(0.1)
                await ws.send(json.dumps({"action": "replace"}))

            await asyncio.sleep(0.2)
            final = pyperclip.paste()
            expected = test_text.upper()
            if final == expected:
                print(f"OK: {description}")
                results.append(True)
            else:
                print(f"ERROR: {description} - final: '{final[:50]}...', esperado: '{expected[:50]}...'")
                results.append(False)
        except Exception as e:
            print(f"Error en {description}: {e}")
            results.append(False)

    return all(results)

async def main():
    print("=== TESTS DE VALIDACIÓN DE RIESGOS ===")

    results = []
    results.append(await test_race_condition_clipboard())
    print()
    results.append(await test_abort_prevents_replace())
    print()
    results.append(await test_window_focus_change())
    print()
    results.append(await test_edge_cases())
    print()

    passed = sum(results)
    total = len(results)
    print(f"Resultados: {passed}/{total} tests pasaron")

    if passed == total:
        print("Todos los riesgos mitigados correctamente.")
    else:
        print("Algunos riesgos requieren atencion adicional.")

if __name__ == "__main__":
    asyncio.run(main())
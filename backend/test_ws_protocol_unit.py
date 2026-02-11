import importlib
import importlib.util
import json
import os
import sys
import types
import unittest
from unittest.mock import patch

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
if HAS_FASTAPI:
    from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(__file__))


def _install_win32_stubs() -> None:
    win32gui_stub = types.ModuleType("win32gui")
    win32gui_stub.GetForegroundWindow = lambda: 111
    win32gui_stub.GetWindowText = lambda hwnd: "Test"
    sys.modules["win32gui"] = win32gui_stub


def _install_input_sim_stubs() -> None:
    input_sim_stub = types.ModuleType("input_sim")
    input_sim_stub.simulate_paste = lambda: None
    input_sim_stub.simulate_select_all = lambda: None
    input_sim_stub.get_active_window_hwnd = lambda: 111
    sys.modules["input_sim"] = input_sim_stub


@unittest.skipUnless(HAS_FASTAPI, "fastapi no disponible")
class WsProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _install_win32_stubs()
        _install_input_sim_stubs()
        if "main" in sys.modules:
            del sys.modules["main"]
        cls.main = importlib.import_module("main")

    def test_replace_without_cycle_returns_no_active_cycle(self):
        with TestClient(self.main.app) as client:
            with client.websocket_connect("/cortex") as ws:
                ws.receive_json()  # connected
                ws.send_text(json.dumps({"action": "replace"}))
                ack = ws.receive_json()
                err = ws.receive_json()
                self.assertEqual(ack["type"], "ack")
                self.assertEqual(err["type"], "error")
                self.assertEqual(err["code"], "NO_ACTIVE_CYCLE")

    def test_replace_with_stale_cycle_returns_cycle_mismatch(self):
        with patch.object(self.main, "simulate_paste", return_value=None), patch.object(
            self.main, "read_clipboard", return_value="hola"
        ), patch.object(self.main, "process_text", return_value="HOLA"), patch.object(
            self.main, "write_clipboard", return_value=None
        ), patch.object(self.main, "get_active_window_hwnd", return_value=111):
            with TestClient(self.main.app) as client:
                with client.websocket_connect("/cortex") as ws:
                    ws.receive_json()  # connected
                    ws.send_text(json.dumps({"action": "paste_cycle"}))
                    ack = ws.receive_json()
                    ws.receive_json()  # step_a
                    ws.receive_json()  # step_b

                    stale_id = ack["cycle_id"] - 1
                    ws.send_text(json.dumps({"action": "replace", "cycle_id": stale_id}))
                    ws.receive_json()  # ack replace
                    err = ws.receive_json()
                    self.assertEqual(err["type"], "error")
                    self.assertEqual(err["code"], "CYCLE_MISMATCH")


if __name__ == "__main__":
    unittest.main()

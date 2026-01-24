from pynput.keyboard import Controller, Key
import win32gui

controller = Controller()

def simulate_paste() -> None:
    """Simula Ctrl+V para pegar."""
    with controller.pressed(Key.ctrl):
        controller.press('v')
        controller.release('v')

def simulate_select_all() -> None:
    """Simula Ctrl+A para seleccionar todo."""
    with controller.pressed(Key.ctrl):
        controller.press('a')
        controller.release('a')

def get_active_window_hwnd() -> int:
    """Obtiene el HWND de la ventana activa."""
    return win32gui.GetForegroundWindow()
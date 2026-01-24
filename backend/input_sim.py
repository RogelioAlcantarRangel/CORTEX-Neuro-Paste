from pynput.keyboard import Controller, Key

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
import pyperclip

def read_clipboard() -> str:
    """Lee el contenido del clipboard."""
    return pyperclip.paste()

def write_clipboard(text: str) -> None:
    """Escribe texto al clipboard."""
    pyperclip.copy(text)

def process_text(text: str) -> str:
    """Procesa el texto: convierte a UPPERCASE (placeholder para lógica futura)."""
    return text.upper()
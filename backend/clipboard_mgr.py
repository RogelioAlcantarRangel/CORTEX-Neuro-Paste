import pyperclip


DEFAULT_RULES = ("uppercase",)


def _apply_uppercase(text: str) -> str:
    return text.upper()


def _apply_trim(text: str) -> str:
    return text.strip()


def _apply_normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def _apply_title_case(text: str) -> str:
    return text.title()


def _apply_remove_line_breaks(text: str) -> str:
    return " ".join(text.splitlines())


TRANSFORMERS = {
    "uppercase": _apply_uppercase,
    "trim": _apply_trim,
    "normalize_spaces": _apply_normalize_spaces,
    "title_case": _apply_title_case,
    "remove_line_breaks": _apply_remove_line_breaks,
}

def read_clipboard() -> str:
    """Lee el contenido del clipboard."""
    return pyperclip.paste()

def write_clipboard(text: str) -> None:
    """Escribe texto al clipboard."""
    pyperclip.copy(text)


def process_text(text: str, rules=DEFAULT_RULES) -> str:
    """Procesa texto usando una pipeline de transformaciones configurables."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    result = text
    for rule in rules:
        transformer = TRANSFORMERS.get(rule)
        if transformer is None:
            continue
        result = transformer(result)
    return result

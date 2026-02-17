import importlib
import sys


class EnvironmentValidationError(RuntimeError):
    """Error de validación del entorno de ejecución."""


def validate_windows_platform(platform: str | None = None) -> None:
    """Valida que el backend se ejecute en Windows."""
    current_platform = platform or sys.platform
    if not current_platform.startswith("win"):
        raise EnvironmentValidationError(
            "CORTEX backend solo es compatible con Windows. "
            f"Plataforma detectada: '{current_platform}'."
        )


def validate_windows_dependencies() -> None:
    """Valida dependencias críticas de Windows y librerías de input."""
    try:
        importlib.import_module("win32gui")
    except ImportError as exc:
        raise EnvironmentValidationError(
            "No se pudo importar 'pywin32' (módulo win32gui). "
            "Instálalo con: 'pip install pywin32' y luego ejecuta "
            "'python -m pywin32_postinstall -install' en una terminal con permisos de administrador."
        ) from exc

    try:
        importlib.import_module("pynput.keyboard")
    except ImportError as exc:
        raise EnvironmentValidationError(
            "No se pudo importar 'pynput'. "
            "Instálalo con: 'pip install pynput'. "
            "Si usas un entorno virtual, asegúrate de activar el mismo entorno donde ejecutas backend/main.py."
        ) from exc


def validate_runtime_environment(platform: str | None = None) -> None:
    """Ejecuta validaciones obligatorias del entorno."""
    validate_windows_platform(platform=platform)
    validate_windows_dependencies()

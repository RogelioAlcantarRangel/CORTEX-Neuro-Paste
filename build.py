#!/usr/bin/env python3
"""
Script de build para compilar backend/main.py a backend.exe usando PyInstaller.
"""

import subprocess
import sys
import os

def build_exe():
    # Comando PyInstaller
    command = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "backend",
        "backend/main.py"
    ]

    # Ejecutar el comando
    try:
        print("Ejecutando PyInstaller para compilar backend.exe...")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Compilación exitosa.")
        print("Salida:", result.stdout)
        if result.stderr:
            print("Errores:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error en la compilación: {e}")
        print("Salida:", e.stdout)
        print("Errores:", e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    build_exe()
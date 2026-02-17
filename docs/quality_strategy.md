# QA, Compatibilidad y Release Gates

## 1) Clasificación de pruebas

### CI automatizado (obligatorio)
- **Lint**: validación estática de backend Python.
- **Unit tests**: lógica de configuración y transformación de clipboard.
- **WebSocket protocol tests**: contrato de mensajes/errores en `/cortex`.

### Smoke tests de entorno (manuales)
Los siguientes scripts quedan **marcados explícitamente** como smoke tests dependientes de entorno:
- `backend/test_risks.py`
- `backend/audit_e2e.py`
- `backend/test_latency.py`

Estos smoke tests requieren:
- Windows con acceso a clipboard real.
- Cambio de foco entre aplicaciones.
- Backend ejecutándose y (cuando aplique) plugin Logitech activo.

## 2) Matriz de compatibilidad de apps objetivo

> Alcance inicial: validación funcional mínima para edición de texto, reemplazo y abort por cambio de foco.

| Categoría | App objetivo | Resultado mínimo requerido para declarar compatibilidad |
|---|---|---|
| Notepad | Windows Notepad | `paste_cycle` pega texto sin bloqueo; `replace` opera sobre ventana activa correcta; `abort` evita reemplazo tras movimiento/foco. |
| Office | Microsoft Word (desktop) | Flujo completo sin pérdida de formato crítico del usuario; no reemplazar si foco cambia; sin errores de protocolo WS. |
| Office | Microsoft Excel (celda en edición) | Pegado y reemplazo estables en celda activa; abort funcional; no colgar input de teclado. |
| IDE | Visual Studio Code | Paste/replace en editor activo; latencia interactiva aceptable; abort al cambiar foco/panel. |
| IDE | JetBrains (IntelliJ/PyCharm) | Equivalente a VS Code: ciclo estable y sin reemplazos cruzados por foco. |

## 3) Release gates objetivos

Una release sólo debe aprobarse si cumple simultáneamente:

- **WS error rate**: `<= 0.5%` de mensajes con `type=error` en sesión de benchmark base.
- **Latencia p95 end-to-end (`paste_cycle`)**: `<= 16 ms`.
- **Estabilidad ante cambio de foco**: `>= 99%` de eventos `replace` correctamente bloqueados cuando la ventana activa cambia respecto al `paste_cycle`.
- **Regresión de protocolo**: 100% de tests de contrato WebSocket en verde.
- **Unit tests**: 100% en verde.

## 4) Versionado de benchmarks por release

Todos los resultados deben almacenarse en `reports/` con convención:

- `reports/<version>/benchmark.md`
- `reports/<version>/raw/*.csv` (opcional)

Ejemplo: `reports/v0.1.0/benchmark.md`

Cada benchmark versionado debe incluir como mínimo:
- Fecha, SO, hardware, versión backend/plugin.
- Tamaño de muestra.
- p50/p95/p99 de latencia.
- WS error rate.
- Resultado de prueba de cambio de foco.
- Apps validadas y observaciones.

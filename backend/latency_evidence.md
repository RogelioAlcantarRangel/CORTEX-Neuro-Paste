# Latency Evidence (versioned)

Este archivo centraliza la evidencia verificable de latencia.

## Scripts fuente

- `backend/test_latency.py` (RTT WebSocket por iteraciones)
- `backend/audit_e2e.py` (auditoría funcional del ciclo paste/proceso)

## Última actualización

- Estado: **pendiente de corrida E2E en entorno Windows con hardware Logitech**.
- Motivo: el entorno actual de documentación no representa el runtime real (inyección de input/clipboard nativa + plugin Options+).

## Plantilla de registro (copiar/pegar por corrida)

```text
Fecha:
Entorno: (equipo, OS, dispositivo Logitech)
Comando ejecutado:
Resumen de salida:
- promedio:
- mínimo:
- máximo:
Observaciones:
```

## Criterio para claims en README/demo

Solo comunicar métricas numéricas como claim si:

1. Se ejecutó script de medición en entorno objetivo.
2. La salida quedó resumida en este archivo.
3. La evidencia está versionada en git.

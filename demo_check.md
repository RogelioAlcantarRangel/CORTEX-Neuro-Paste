# Demo Check: verificación de CORTEX Neuro-Paste

Checklist para validar la demo con jueces/clientes de forma repetible.

## Prerrequisitos

- Dispositivo Logitech MX reconocido por Logitech Options+.
- Windows 10/11.
- Backend disponible (ejecución por `python backend/main.py` o binario empaquetado).

## 1) Levantar backend

- Iniciar backend.
- Verificar que el endpoint WS responde en `ws://localhost:8989/cortex`.

## 2) Configurar plugin

- Copiar `plugin/` al directorio de plugins de Logitech Options+.
- Reiniciar Logitech Options+.
- Asignar acción **CORTEX Neuro-Paste** a un botón.
- Confirmar `ws_url = ws://localhost:8989/cortex`.

## 3) Verificación funcional rápida

- Abrir editor de texto (Notepad recomendado).
- Copiar `hello world` al clipboard.
- Pulsación corta: debe pegar inmediatamente.
- Hold > umbral configurado: debe aplicar transformación configurada (ej. `HELLO WORLD` si `uppercase`).
- Movimiento durante hold: debe cancelar `replace`.

## 4) Evidencia de latencia (medible)

- Ejecutar scripts de medición:
  - `backend/test_latency.py`
  - `backend/audit_e2e.py`
- Registrar el resultado en `backend/latency_evidence.md` con:
  - fecha/hora
  - entorno (HW/OS)
  - comando
  - salida resumida (al menos promedio y máximos)

> Nota: no usar cifras de latencia como claim final si no están registradas y versionadas en `backend/latency_evidence.md`.

## 5) Verificación de robustez

- **Abort safety:** `paste_cycle` + `abort` + `replace` no debe generar reemplazo destructivo.
- **Sin crash visible:** desconectar backend y verificar degradación controlada en plugin.
- **Integridad clipboard:** probar caracteres especiales y multilinea.

## 6) Mensaje para demo

- Enfatizar que CORTEX prioriza feedback inmediato.
- Reportar estado real: objetivos de latencia + última evidencia versionada.
- Si hay desviaciones, mostrar limitaciones conocidas y plan de mitigación (`PLAN_CLIENTES.md`).

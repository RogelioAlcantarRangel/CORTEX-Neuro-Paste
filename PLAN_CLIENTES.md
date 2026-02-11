# Plan de funciones faltantes para llevar CORTEX a presentación con clientes

Este plan identifica las brechas actuales del proyecto y prioriza las funciones necesarias para una demo comercial estable, repetible y segura.

## 1) Diagnóstico actual (base del plan)

- El backend ya implementa el ciclo principal `paste_cycle` → proceso async → `replace`/`abort`.  
- El procesamiento de texto aún es un **placeholder** (`text.upper()`), por lo que no existe valor real configurable para clientes.  
- No hay canal de respuesta estructurado backend→plugin (ACK/estado/error), lo que limita monitoreo, telemetría y tests de latencia fiables.  
- La configuración está hardcodeada (`ws://localhost:8989/cortex`, umbrales de tiempo), sin perfil por cliente/equipo.  
- Falta packaging/release con checklist de instalación y observabilidad mínima para soporte post-demo.

## 2) Objetivo de salida para "listo para clientes"

Al finalizar este plan, el producto debe cumplir:

1. Demo estable en Windows 10/11 por 30 minutos sin reinicios.
2. Flujo configurable por perfil (latencia, hold, transformación de texto).
3. Trazabilidad básica (logs y eventos de error entendibles).
4. Guía de instalación/recovery de 1 página para pre-venta y soporte.

---

## 3) Backlog priorizado de funciones faltantes

## Fase 1 — Crítico para demo comercial (Semana 1)

### F1. Motor de transformaciones real (no placeholder)
**Problema actual:** `process_text` solo aplica uppercase.  
**Función faltante:** pipeline de transformaciones con reglas seleccionables.

**Entregables:**
- Estrategia de transformaciones (`uppercase`, `trim`, `normalize_spaces`, `title_case`, `remove_line_breaks`).
- Selección por configuración (orden y on/off por regla).
- Manejo seguro de clipboard vacío/no-texto.

**Criterio de aceptación:**
- Dado un perfil de reglas, el texto resultante coincide 100% con casos de prueba predefinidos.

### F2. Protocolo WebSocket con ACK y errores tipados
**Problema actual:** el backend no responde mensajes de estado al plugin.
**Función faltante:** respuesta estructurada por evento para visibilidad operativa.

**Entregables:**
- Contrato JSON mínimo:
  - `ack`: `{"type":"ack","action":"paste_cycle","ts":...}`
  - `status`: `{"type":"status","phase":"step_b_done"}`
  - `error`: `{"type":"error","code":"WINDOW_MISMATCH"}`
- Correlation ID por ciclo para depuración.
- Plugin manejando ACK/errores sin bloquear UX.

**Criterio de aceptación:**
- 100 ciclos consecutivos con trazas completas (inicio/proceso/fin o error) sin desconexión.

### F3. Configuración externa por archivo
**Problema actual:** URL, umbrales y comportamiento están hardcodeados.
**Función faltante:** sistema de configuración local editable.

**Entregables:**
- Archivo `backend/config.json` o `.env` con:
  - `ws_host`, `ws_port`
  - `hold_threshold_ms`, `mouse_abort_debounce_ms`
  - reglas de transformación activas
- Validación de esquema y fallback a defaults seguros.

**Criterio de aceptación:**
- Cambiar umbral de hold o reglas sin tocar código y ver efecto al reiniciar servicio.

### F4. Logs operativos para demo y soporte
**Problema actual:** mezcla de `print` sin estructura.
**Función faltante:** logging estructurado y niveles homogéneos.

**Entregables:**
- Logger con formato consistente (`timestamp`, `level`, `event`, `latency_ms`, `connection_id`).
- Rotación simple de archivo de log.
- Modo `--debug` para demo técnica.

**Criterio de aceptación:**
- Un incidente de demo (disconnect, abort, mismatch) se diagnostica en <5 minutos leyendo logs.

---

## Fase 2 — Confiabilidad y calidad percibida (Semana 2)

### F5. Suite de pruebas automatizadas por niveles
**Función faltante:** cobertura sistemática de unidad + integración.

**Entregables:**
- Unit tests para transformaciones de texto.
- Integración WebSocket (acciones válidas/inválidas, ordering, abort race).
- Smoke test para reconexión plugin-backend.

**Criterio de aceptación:**
- Pipeline local de pruebas verde en entorno Windows de referencia.

### F6. Guardas de seguridad UX
**Función faltante:** protección explícita contra reemplazos destructivos.

**Entregables:**
- Timeout máximo entre `paste_cycle` y `replace`.
- Validación de foco/ventana reforzada.
- Modo "safe replace" opcional (solo si contenido cambió y pasó validaciones).

**Criterio de aceptación:**
- En pruebas de stress con cambios de foco, 0 reemplazos no intencionales.

### F7. Métricas de rendimiento de cara a clientes
**Función faltante:** KPIs objetivos de latencia y estabilidad.

**Entregables:**
- Script único de benchmark para:
  - `keyDown→paste`
  - `step_b_processing`
  - `replace`
- Reporte resumido (p50/p95/p99) exportable.

**Criterio de aceptación:**
- Reporte reproducible con evidencia de cumplimiento de SLA demo.

---

## Fase 3 — Producto presentable y replicable (Semana 3)

### F8. Instalador y operación simplificada
**Función faltante:** experiencia de despliegue de un clic.

**Entregables:**
- Build script reproducible para backend empaquetado.
- Guía de instalación + troubleshooting para equipo comercial.
- Script de "health check" (puerto abierto, websocket activo, plugin detectado).

**Criterio de aceptación:**
- Un tercero instala y ejecuta la demo en <15 minutos con la guía.

### F9. Perfiles por tipo de cliente
**Función faltante:** presets para distintos contextos de uso.

**Entregables:**
- Perfiles (ej.: "Ofimática", "Soporte", "Escritura rápida").
- Cambio de perfil por archivo de config.

**Criterio de aceptación:**
- Demo comparativa entre dos perfiles sin recompilar.

### F10. Material comercial-técnico
**Función faltante:** paquete mínimo para conversación con cliente.

**Entregables:**
- One-pager con propuesta de valor + límites conocidos.
- Matriz de riesgos y mitigaciones.
- Script de demo de 5 minutos (normal + contingencia).

**Criterio de aceptación:**
- Equipo comercial puede ejecutar narrativa y demo sin soporte del equipo técnico.

---

## 4) Dependencias y orden recomendado

1. **F1 + F2 + F3** primero (valor funcional + control + observabilidad).  
2. **F4 + F5 + F6** después (estabilidad demostrable).  
3. **F7 + F8 + F9 + F10** para cerrar con narrativa comercial y despliegue repetible.

Ruta crítica: **F2 (ACK/protocolo)** y **F3 (configuración)** desbloquean pruebas, métricas y soporte.

## 5) Riesgos principales y mitigación

- **Riesgo:** diferencias de comportamiento por app objetivo (Notepad vs Office vs IDE).  
  **Mitigación:** matriz de apps objetivo y validación por perfil.
- **Riesgo:** regresiones de latencia por instrumentación.  
  **Mitigación:** benchmarks automáticos por commit en entorno de referencia.
- **Riesgo:** errores por cambio de foco/ventana durante hold.  
  **Mitigación:** guardas de ventana + timeout de ciclo + abort robusto.

## 6) Definición de "Done" para presentar a clientes

Se considera listo para clientes cuando:

- Existe transformación de texto configurable y útil (no placeholder).
- Hay contrato WS con ACK/error verificable.
- Configuración externa permite ajustar demo sin cambiar código.
- Hay evidencia de latencia/estabilidad con reporte reproducible.
- La instalación y recuperación están documentadas para no ingenieros.

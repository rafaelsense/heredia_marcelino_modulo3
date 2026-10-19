# Registro de hitos — LOG-001

## Hito 01 — Separar responsabilidades

**Estado:** completado y pendiente de revisión del estudiante.

### Qué se construyó

- Paquete instalable con estructura `src/agente_logistico` y gestión mediante `uv`.
- Configuración de `CASO_ID=LOG-001`, variante Logística y `SEMILLA=6739`.
- Parámetros reproducibles: capacidad diaria 6, ventana estándar 3 días hábiles y costo extraordinario USD 400.
- Base SQLite sintética con clientes, productos, inventario, ventas, reservas de capacidad y parámetros del escenario.
- Reglas deterministas para entrega directa, despacho extraordinario y rechazo de negocio.
- Docstrings breves en español para los contratos y funciones relevantes, siguiendo el estilo de las sesiones.
- Diez solicitudes clasificadas por capacidad y justificación en `docs/responsabilidades.md`.
- Dieciocho pruebas de configuración, reinicio, datos, reglas y entradas inválidas.

### Qué falló

No se registraron fallos funcionales en esta etapa. La primera instalación mostró una advertencia de `uv` porque no pudo usar enlaces duros entre sistemas de archivos y utilizó copias; la instalación terminó correctamente y una segunda ejecución auditó los siete paquetes sin errores.

### Qué aprendí

La semilla debe generar parámetros mediante una secuencia fija y aislada de otros usos de aleatoriedad. Las pruebas de reinicio verifican reproducibilidad mejor que una simple inspección del código. También queda clara la separación entre datos transaccionales, reglas objetivas y futuras fuentes documentales.

### Qué decisión cambió después de probar

Ninguna regla de negocio necesitó cambios después de las pruebas: los 18 casos confirmaron el comportamiento previsto. Antes de implementar, la revisión del plan sí cambió la estructura plana por un paquete `src` y eliminó nombres de archivos con `demo` para describir mejor las responsabilidades.

### Evidencia

- `EVIDENCIAS.md`
- `evidencias/hito01_uv_sync.txt`
- `evidencias/hito01_configuracion.txt`
- `evidencias/hito01_datos.txt`
- `evidencias/hito01_pytest.txt`
- `docs/responsabilidades.md`

## Hito 02 — Router + RAG + SQL + Tools

**Estado:** pendiente de autorización.

## Hito 03 — Workflow con estado

**Estado:** pendiente.

## Hito 04 — Retry, checkpoint y HITL

**Estado:** pendiente.

## Hito 05 — MCP: desacoplar

**Estado:** pendiente.

## Hito 06 — Integración y reflexión

**Estado:** pendiente.

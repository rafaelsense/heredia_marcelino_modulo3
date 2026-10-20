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

**Estado:** completado y pendiente de revisión del estudiante.

### Qué se construyó

- Contratos tipados para seis destinos: RAG, SQL, TOOLS, WORKFLOW, CLARIFY y DIRECT.
- Router determinista, router por modelo y router híbrido con reducción de tools por ruta.
- Dos documentos de políticas logísticas, índice RAG local, caché por contenido/modelo, fuentes citables y abstención por baja relevancia.
- Capa única `servicios.py` con cliente, disponibilidad, capacidad y resumen histórico de ventas.
- Tres tools semánticas: `consultar_cliente`, `consultar_disponibilidad` y `consultar_capacidad_despacho`.
- SQL parametrizado con filtros por SKU, cliente y rango de fechas.
- Doce casos de evaluación del router y 54 pruebas automatizadas.

### Qué falló

- `openai-agents 0.24.0` y `0.0.19` fallaron al importarse con Python 3.11.0 (`KeyError: ~TContext`). La versión importable más reciente comprobada fue `0.0.17`.
- Con `openai 3.35.1`, la creación de `RunContextWrapper` falló por el campo `cache_write_tokens`; la combinación verificada fue `openai-agents==0.0.17` con `openai==2.9.0`.
- La primera evaluación del router obtuvo 10/12. “Existencias” fue enviado a aclaración por falta de vocabulario y “¿Qué significa SKU?” fue enviado a tools por la palabra SKU.

### Qué aprendí

Las reglas del router son auditables, pero su vocabulario debe evaluarse con paráfrasis. También comprobé que una dependencia que se instala correctamente puede fallar al importarse o al crear objetos; la compatibilidad debe probarse con el runtime real, no solo con `uv sync`.

### Qué decisión cambió después de probar

- Se añadió “existencias” como término operativo.
- Las preguntas conceptuales se evalúan antes que las operativas para evitar que “SKU” active una tool.
- Se fijaron versiones compatibles de OpenAI Agents SDK y OpenAI en `pyproject.toml`.

### Evidencia

- `evidencias/hito02_uv_sync.log`
- `evidencias/hito02_versiones.log`
- `evidencias/hito02_router_error_vocabulario.log`
- `evidencias/hito02_router.log`
- `evidencias/hito02_capacidades.log`
- `evidencias/hito02_pytest.log`
- `DECISIONES.md`

La ejecución real del modelo/híbrido y del índice RAG con OpenAI quedó pendiente porque no hay `OPENAI_API_KEY` configurada; las pruebas de RAG usan embeddings deterministas sin red y no se presentan como una llamada real al proveedor.

## Hito 03 — Workflow con estado

**Estado:** pendiente.

## Hito 04 — Retry, checkpoint y HITL

**Estado:** pendiente.

## Hito 05 — MCP: desacoplar

**Estado:** pendiente.

## Hito 06 — Integración y reflexión

**Estado:** pendiente.

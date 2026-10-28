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

~~La ejecución real del modelo/híbrido y del índice RAG con OpenAI quedó pendiente porque no hay `OPENAI_API_KEY` configurada~~ **Actualización posterior:** se ejecutó con Gemini (`gemini-3.5-flash-lite` y `gemini-embedding-001`): router `model` 12/12, router `hybrid` 12/12 y RAG real con abstención calibrada (`RAG_MIN_SCORE=0.65`). Evidencias: `evidencias/hito02_router_model_gemini.log`, `evidencias/hito02_router_hybrid_gemini.log` y `evidencias/hito02_rag_gemini.log`. Las pruebas de RAG usan embeddings deterministas sin red y no se presentan como una llamada real al proveedor.

## Hito 03 — Workflow con estado

**Estado:** completado y pendiente de revisión del estudiante.

### Qué se construyó

- Grafo LangGraph con nueve nodos: `extraer_solicitud`, `cargar_datos_operativos`, `consultar_capacidad`, `recuperar_politica`, `evaluar_reglas`, `confirmar_compromiso`, `marcar_excepcion`, `cerrar_rechazo` y `cerrar_aclaracion`.
- Tres aristas condicionales: tras extracción (aclaración o datos), tras datos operativos (rechazo anticipado o capacidad) y tras evaluación (directo, excepción o rechazo).
- Estado tipado `EstadoLogistico` con identidad del caso, sustento de la decisión, fuentes citables acumulativas y marcador de aprobación para el HITL del Hito 04.
- Contrato `SolicitudLogistica` con validación Pydantic de cliente, SKU, cantidad positiva y fecha ISO.
- Extractor LLM inyectable; el modo offline usa entrada estructurada y el embedder léxico local, sin llamadas externas.
- CLI `python -m agente_logistico` con `--id-hilo`, campos estructurados o `--solicitud` en lenguaje natural.
- Documentación del grafo con diagrama Mermaid y justificación del estado en `docs/workflow.md`.
- Doce pruebas nuevas del workflow; la suite completa llega a 66 pruebas.

### Qué falló

La consola de Windows mostró caracteres acentuados corruptos al capturar salidas (`estándar` como `estndar`); se resolvió capturando las evidencias con `PYTHONIOENCODING=utf-8`. No hubo fallos funcionales: `langgraph 1.2.17` se integró sin conflicto con los pins `openai-agents==0.0.17` y `openai==2.9.0`.

### Qué aprendí

Las salidas anticipadas (cliente bloqueado, SKU inexistente) son más claras como aristas condicionales que como excepciones dentro de los nodos. También comprobé que la caché RAG debe separarse por tipo de embedder: el índice léxico offline usa `.cache/politicas_index_lexico.json` para no mezclar dimensiones con el índice de OpenAI.

### Qué decisión cambió después de probar

El nodo `recuperar_politica` degrada con advertencia en lugar de abortar cuando no hay credenciales: la decisión del compromiso depende de reglas deterministas, no del documento recuperado. Se añadió el embedder léxico solo como vía de demostración offline; la recuperación de producción sigue siendo la de OpenAI.

### Evidencia

- `evidencias/hito03_uv_sync.log`
- `evidencias/hito03_versiones.log`
- `evidencias/hito03_pytest.log`
- `evidencias/hito03_cli_directo.log`
- `evidencias/hito03_cli_excepcion.log`
- `evidencias/hito03_cli_rechazo.log`
- `evidencias/hito03_cli_bloqueado.log`
- `docs/workflow.md`

~~La extracción con LLM en lenguaje natural quedó pendiente porque no hay `OPENAI_API_KEY` configurada~~ **Actualización posterior:** se ejecutó con Gemini real. `demo-llm-directo` (“C-1003 necesita 6 EDGE-ORIN para el 2026-03-19”) terminó `confirmado` y `demo-llm-gemini` (“C-1004 pide 12 EDGE-ORIN urgente para el 2026-03-17”) terminó `pendiente_aprobacion` con costo USD 400. Evidencias: `evidencias/hito03_cli_llm_directo_gemini.log` y `evidencias/hito03_cli_llm_excepcion_gemini.log`. Las ejecuciones offline usan entrada estructurada y el embedder léxico, y no se presentan como llamadas reales al proveedor.

## Hito 04 — Retry, checkpoint y HITL

**Estado:** completado y pendiente de revisión del estudiante.

### Qué se construyó

- `reintento.py`: retry con backoff exponencial y jitter, solo para errores transitorios (429 cuota/minuto, 503 alta demanda, fallos de red), en versión síncrona y asíncrona.
- Simulación determinista de fallo transitorio (`SIMULAR_FALLO_TRANSITORIO_CAPACIDAD=1`) que falla una sola vez por hilo, para evidenciar el retry sin gastar cuota de API.
- Retry aplicado en tres nodos: extracción LLM, capacidad de despacho y recuperación de políticas.
- Checkpoint persistente con `AsyncSqliteSaver` en `data/checkpoints.db`; `--id-hilo` es el hilo del grafo.
- HITL real: nuevo nodo `esperar_aprobacion` pausa el grafo con `interrupt()`; el supervisor reanuda con `--reanudar --decision aprobado|rechazado --supervisor "Nombre"`.
- El grafo pasa a 10 nodos y 4 aristas condicionales (la cuarta enruta la decisión humana).
- Diez pruebas nuevas; la suite completa llega a 79.

### Qué falló

La integración real con Gemini había mostrado 429 (cuota por minuto) y 503 (alta demanda): exactamente los errores que este hito trata como transitorios. Además, el primer diseño ponía el `interrupt()` en el mismo nodo que marcaba la excepción, y el estado pausado no reflejaba `pendiente_aprobacion`; se separó en `marcar_excepcion` (publica el estado) y `esperar_aprobacion` (pausa).

### Qué aprendí

`interrupt()` exige checkpointer: sin persistencia no hay pausa real, solo una detención. También que el retry debe distinguir errores transitorios de errores de negocio: reintentar un "stock insuficiente" sería un error de diseño, no de red.

### Qué decisión cambió después de probar

El rechazo por decisión del supervisor necesita su propio mensaje: `cerrar_rechazo` ahora distingue el rechazo de reglas (motivo de negocio) del rechazo humano (supervisor y comentario).

### Evidencia

- `evidencias/hito04_retry_simulado.log` (fallo transitorio → retry → `confirmado`)
- `evidencias/hito04_hitl_pausa.log` (excepción pausada con instrucción de reanudación)
- `evidencias/hito04_hitl_aprobado.log` (reanudación aprobada → despacho extraordinario confirmado, USD 400)
- `evidencias/hito04_hitl_rechazado.log` (reanudación rechazada → cierre con motivo del supervisor)
- `evidencias/hito04_pytest.log` (79 passed)

La pausa HITL se demostró entre procesos distintos: la reanudación lee el checkpoint SQLite sin repetir los nodos anteriores.

## Hito 05 — MCP: desacoplar

**Estado:** pendiente.

## Hito 06 — Integración y reflexión

**Estado:** pendiente.

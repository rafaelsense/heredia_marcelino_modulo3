# Evidencias de ejecución — LOG-001

Las evidencias se generan ejecutando el proyecto; no se copian resultados de otros casos. Los archivos de salida se encuentran en `evidencias/`.

## Hito 01

### Instalación del paquete

```bash
uv sync
```

Resultado: resolución y auditoría correcta de siete paquetes; el paquete `agente-logistico-log001` quedó instalado en el entorno local. Salida: `evidencias/hito01_uv_sync.txt`.

### Configuración y reproducibilidad

```bash
uv run python -m agente_logistico.config_caso
uv run python -m agente_logistico.config_caso
```

Las dos ejecuciones independientes producen el mismo resultado:

```text
CASO_ID: LOG-001
VARIANTE: Logística
SEMILLA: 6739
Capacidad diaria: 6
Ventana de entrega: 3 días hábiles
Costo extraordinario: USD 400
Fecha de referencia: 2026-03-16
```

Salida completa: `evidencias/hito01_configuracion.txt`. Además, `tests/test_config_caso.py` compara automáticamente la salida de dos procesos independientes.

### Inicialización de datos

```bash
uv run python -m agente_logistico.inicializar_datos
```

Resultado: base `data/logistica.db` recreada con 1 configuración, 3 clientes, 2 productos, 2 registros de inventario, 6 ventas y 2 reservas de capacidad. Salida: `evidencias/hito01_datos.txt`.

La base es un artefacto local ignorado por Git. `tests/test_inicializar_datos.py` comprueba que, después de modificar un stock y reinicializar, se restauran exactamente los datos iniciales.

### Pruebas

```bash
uv run pytest
```

Resultado: **18 passed**. La salida completa está en `evidencias/hito01_pytest.txt`.

Cobertura de esta etapa:

- Valores exactos asociados a `LOG-001` y semilla `6739`.
- Repetición de parámetros y reinicio de procesos.
- Datos mínimos y recreación de la base.
- Ruta directa de 6 unidades.
- Excepción de 12 unidades con costo USD 400.
- Rechazo por stock, capacidad y fecha.
- Efecto de reservas sobre la capacidad.
- Parámetros inválidos y cálculo de días hábiles.

### Separación manual de responsabilidades

La tabla de diez consultas y las respuestas sobre reglas, datos y fuentes se encuentran en `docs/responsabilidades.md`.

### Alcance de la verificación

El Hito 01 se ejecutó sin APIs externas ni credenciales. Router, RAG, SQL como capacidad del agente, tools semánticas, workflow y MCP pertenecen a hitos posteriores y no se presentan como implementados.

## Hito 02

### Instalación y versiones

```bash
uv sync
```

Resultado final: 48 paquetes auditados. Salida: `evidencias/hito02_uv_sync.log`.

Durante la validación se detectaron incompatibilidades reales del runtime. La combinación final comprobada es:

```text
openai-agents=0.0.17
openai=2.9.0
imports=OK
```

Salida: `evidencias/hito02_versiones.log`.

### Error del router y corrección

```bash
uv run python -m agente_logistico.evaluacion_router --strategy deterministic
```

Primera ejecución: **10/12** casos correctos. Fallaron:

1. `¿Qué existencias hay de EDGE-ORIN en ALM-LIM?` → esperado `tools`, obtenido `clarify`.
2. `¿Qué significa SKU?` → esperado `direct`, obtenido `tools`.

Causa: vocabulario operativo incompleto y prioridad de la palabra SKU sobre la intención conceptual. Evidencia: `evidencias/hito02_router_error_vocabulario.log`.

Después de añadir “existencias” y clasificar primero las preguntas conceptuales, la misma suite obtuvo **12/12**. Evidencia: `evidencias/hito02_router.log`.

### SQL y tools semánticas

Se ejecutaron ejemplos reales sobre la base SQLite para cliente, stock insuficiente, capacidad extraordinaria, resumen filtrado y un valor con aspecto malicioso tratado como parámetro. Salida: `evidencias/hito02_capacidades.log`.

Resultados principales:

- `C-1003` existe y está activo.
- 40 unidades frente a stock 30 devuelven `suficiente: false`, sin inventar disponibilidad.
- 12 unidades no caben en capacidad normal 6, pero sí en capacidad extraordinaria 12.
- `EDGE-ORIN + C-1003` devuelve 2 ventas, 12 unidades y USD 22,800.
- `EDGE-ORIN' OR 1=1 --` devuelve cero coincidencias porque viaja como valor parametrizado.

### RAG

Las pruebas de RAG usan embeddings deterministas inyectados y una base temporal para no llamar a la red. Comprueban:

- Recuperación de la política de compromiso.
- Recuperación de la política extraordinaria.
- Abstención ante evidencia irrelevante.
- Una consulta de stock enrutada a `TOOLS`, no a RAG.

No se reconstruyó el índice real con OpenAI porque `OPENAI_API_KEY` no está configurada en el entorno del proyecto. Esta limitación se registra explícitamente; no se sustituyó por una salida simulada.

### Pruebas completas

```bash
uv run pytest
```

Resultado: **54 passed**. Salida: `evidencias/hito02_pytest.log`.

La cobertura acumulada incluye Hito 01, contratos, 12 rutas, RAG, servicios SQL, tres tools semánticas, errores de datos y orquestación segura de `CLARIFY`/`WORKFLOW`.

## Hito 03

### Instalación y versiones

```bash
uv sync
```

Se añadió `langgraph` sin conflicto con los pins existentes. Combinación comprobada:

```text
langgraph=1.2.17
langgraph-checkpoint=4.3.0
openai-agents=0.0.17
openai=2.9.0
```

Salidas: `evidencias/hito03_uv_sync.log` y `evidencias/hito03_versiones.log`.

### Ejecución del workflow (modo offline)

Las cuatro rutas del grafo se ejecutaron con entrada estructurada y el embedder léxico local, sin credenciales externas:

```bash
uv run python -m agente_logistico --cliente C-1003 --sku EDGE-ORIN --cantidad 6 --fecha 2026-03-19 --id-hilo demo-directo --offline
uv run python -m agente_logistico --cliente C-1004 --sku EDGE-ORIN --cantidad 12 --fecha 2026-03-17 --id-hilo demo-excepcion --offline
uv run python -m agente_logistico --cliente C-1003 --sku EDGE-ORIN --cantidad 40 --fecha 2026-03-19 --id-hilo demo-rechazo --offline
uv run python -m agente_logistico --cliente C-1005 --sku CAM-IP67 --cantidad 2 --fecha 2026-03-19 --id-hilo demo-bloqueado --offline
```

Resultados:

- **Directo** (`demo-directo`): estado `confirmado`, 6 unidades dentro de ventana estándar y capacidad normal 6. Evidencia: `evidencias/hito03_cli_directo.log`.
- **Excepción** (`demo-excepcion`): estado `pendiente_aprobacion`, despacho extraordinario con costo USD 400 y marcador de aprobación del supervisor. Evidencia: `evidencias/hito03_cli_excepcion.log`.
- **Rechazo por stock** (`demo-rechazo`): 40 unidades frente a stock 30, estado `rechazado` sin retry. Evidencia: `evidencias/hito03_cli_rechazo.log`.
- **Rechazo anticipado** (`demo-bloqueado`): cliente C-1005 bloqueado; el grafo cierra sin evaluar capacidad ni reglas. Evidencia: `evidencias/hito03_cli_bloqueado.log`.

En los cuatro casos el estado final incluye las fuentes `[SQL:clientes]`, `[SQL:inventario]`, `[SQL:reservas_capacidad]` y, cuando el flujo llegó al nodo documental, referencias `[RAG:...]` recuperadas con el embedder léxico offline.

### Pruebas completas

```bash
uv run pytest
```

Resultado: **66 passed**. Salida: `evidencias/hito03_pytest.log`.

Cobertura nueva del Hito 03:

- Ruta directa confirmada con fuentes SQL y RAG.
- Excepción pendiente de aprobación con costo USD 400.
- Rechazos por stock insuficiente, cliente bloqueado y SKU inexistente.
- Extracción inválida y entrada estructurada inválida derivan a aclaración sin ejecutar tools.
- Sin extractor ni estructura, el workflow pide aclaración en lugar de fallar.
- Las tres decisiones de negocio enrutan a ramas distintas.
- El estado final no contiene claves ni campos fuera del contrato.
- El grafo expone al menos nueve nodos.

La extracción con LLM desde lenguaje natural no se ejecutó porque `OPENAI_API_KEY` no está configurada; el extractor es inyectable y queda listo para cuando se configure la credencial.

## Ejecución real con Gemini (posterior al Hito 03)

Con `MODEL_PROVIDER=gemini`, `PROVIDER_API_KEY` y `MODEL_NAME=gemini-3.5-flash-lite` se repitieron las verificaciones contra el proveedor real:

### Router por modelo e híbrido

```bash
uv run python -m agente_logistico.evaluacion_router --strategy model --delay 13
uv run python -m agente_logistico.evaluacion_router --strategy hybrid --delay 13
```

Resultado: **12/12 (accuracy 1.0) en ambas estrategias**. El `--delay 13` respeta el límite del nivel gratuito (5 solicitudes/minuto). Evidencias: `evidencias/hito02_router_model_gemini.log` y `evidencias/hito02_router_hybrid_gemini.log`.

### RAG real con embeddings de Gemini

`gemini-embedding-001` (3072 dimensiones) recupera la política correcta con scores 0.74–0.84 y se abstiene ante texto irrelevante con `RAG_MIN_SCORE=0.65` (su similitud coseno base es ~0.57, mayor que el umbral por defecto 0.25; la calibración quedó registrada como decisión de ingeniería). Evidencia: `evidencias/hito02_rag_gemini.log`.

### Calibración medible del umbral de abstención

```bash
uv run python -m agente_logistico.calibracion_rag
```

El módulo `calibracion_rag.py` ejecuta 12 consultas etiquetadas (`data/rag_calibracion.json`: 6 relevantes, 6 irrelevantes), mide el mejor score de cada una y recomienda el umbral como el punto medio del hueco entre grupos. Resultado con `gemini-embedding-001`:

```text
min_relevante:      0.7088
max_irrelevante:    0.5907
separable:          True
umbral_recomendado: 0.65   (margen: 0.059 a cada lado)
umbral_actual:      0.65
```

La recomendación coincide con el valor configurado. Si los grupos se solaparan, el comando informaría el solapamiento y saldría con código de error en lugar de recomendar un umbral engañoso. Evidencia completa: `evidencias/hito02_rag_calibracion_gemini.log`.

### Workflow end-to-end en lenguaje natural

```bash
uv run python -m agente_logistico --id-hilo demo-llm-directo --solicitud "Andes Manufactura (C-1003) necesita 6 computadoras EDGE-ORIN para el 2026-03-19"
uv run python -m agente_logistico --id-hilo demo-llm-gemini --solicitud "Talleres Norte (C-1004) pide 12 EDGE-ORIN urgente para el 2026-03-17"
```

- `demo-llm-directo` → `confirmado` (extracción LLM correcta, despacho normal). Evidencia: `evidencias/hito03_cli_llm_directo_gemini.log`.
- `demo-llm-gemini` → `pendiente_aprobacion` con costo USD 400 (el LLM interpretó “urgente” y la fecha temprana activó la ruta extraordinaria). Evidencia: `evidencias/hito03_cli_llm_excepcion_gemini.log`.

### Incidencias reales de la integración con Gemini

1. `PROVIDER_BASE_URL` sin esquema `https://` producía `UnsupportedProtocol`; el código ahora lo tolera.
2. `gemini-3.8-flash` (preview) respondió 503 por alta demanda.
3. `gemini-3.6-flash` agotó su cuota diaria del nivel gratuito (20 solicitudes/día).
4. `gemini-2.5-flash-lite`, el más barato del catálogo, ya no está disponible para claves nuevas (404); la API recomienda `gemini-3.5-flash-lite`.

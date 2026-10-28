# Agente logístico — LOG-001

Proyecto del Módulo 3 para evaluar compromisos de entrega B2B de AndesSupply.

- **Estudiante:** Marcelino Rafael Heredia Garcia
- **Variante:** Logística
- **Caso:** `LOG-001`
- **Semilla:** `6739`
- **Estado actual:** Hito 04, Retry + checkpoint + HITL

La semilla determina la capacidad diaria, la ventana estándar de entrega y el costo del despacho extraordinario. Los datos son sintéticos y la fecha de referencia es fija para que las ejecuciones sean reproducibles.

## Requisitos

- Python 3.11 o superior
- [uv](https://docs.astral.sh/uv/)

Las pruebas, el router determinista y el workflow en modo offline no necesitan credenciales. Para ejecutar el router por modelo/híbrido, reconstruir el índice RAG real o extraer solicitudes en lenguaje natural, copia `.env.example` como `.env` y configura `PROVIDER_API_KEY`; el archivo `.env` no se versiona.

Por compatibilidad comprobada con Python 3.11.0, el proyecto fija `openai-agents==0.0.17` y `openai==2.9.0`.

## Instalación y verificación

Ejecutar desde esta carpeta:

```bash
uv sync
uv run python -m agente_logistico.config_caso
uv run python -m agente_logistico.inicializar_datos
uv run pytest
uv run python -m agente_logistico.evaluacion_router --strategy deterministic
```

Resultados actuales: 79 pruebas verdes y 12/12 casos del router en las tres estrategias (determinista, modelo e híbrido, estas dos con Gemini real).

`inicializar_datos` recrea únicamente la base sintética `data/logistica.db`. Esta base, `.env` y los entornos locales están excluidos de Git.

## Workflow de compromiso de entrega

```bash
# Offline, sin credenciales: entrada estructurada + embedder léxico
uv run python -m agente_logistico --cliente C-1003 --sku EDGE-ORIN \
  --cantidad 6 --fecha 2026-03-19 --id-hilo demo-directo --offline

# Con PROVIDER_API_KEY: solicitud en lenguaje natural
uv run python -m agente_logistico --id-hilo demo-llm \
  --solicitud "Andes Manufactura (C-1003) necesita 6 EDGE-ORIN para el 2026-03-19"
```

El grafo, sus nodos y la justificación del estado se describen en `docs/workflow.md`. Las ejecuciones usan checkpoint SQLite (`data/checkpoints.db`): si una excepción queda `pendiente_aprobacion`, el supervisor la reanuda desde otro proceso:

```bash
uv run python -m agente_logistico --reanudar --id-hilo <ID> \
  --decision aprobado --supervisor "María Torres" --offline
```

## Credenciales opcionales

```powershell
Copy-Item .env.example .env
```

El proyecto admite dos proveedores, seleccionados con `MODEL_PROVIDER` en `.env`. La clave siempre va en `PROVIDER_API_KEY`, sea cual sea el proveedor:

- **OpenAI** (por defecto): `MODEL_PROVIDER=openai` y tu clave en `PROVIDER_API_KEY` (se acepta `OPENAI_API_KEY` como alias de compatibilidad).
- **Gemini** (endpoint OpenAI-compatible): `MODEL_PROVIDER=gemini` y tu clave de Google AI Studio en `PROVIDER_API_KEY`.

`MODEL_NAME` y `EMBEDDING_MODEL` tienen valores por defecto por proveedor (`gpt-4.1-mini`/`text-embedding-3-small` para OpenAI; `gemini-3.5-flash-lite`/`gemini-embedding-001` para Gemini) y solo hace falta definirlos para cambiarlos. Se eligió `gemini-3.5-flash-lite` por ser el más económico disponible para claves nuevas: `gemini-2.5-flash-lite` ya no se ofrece a usuarios nuevos, `gemini-3.6-flash` agota su cuota diaria del nivel gratuito (20 solicitudes/día) y `gemini-3.8-flash` (vista previa) respondió 503 por alta demanda durante las pruebas.

Después de completar la clave en `.env`, pueden compararse las otras estrategias:

```bash
uv run python -m agente_logistico.evaluacion_router --strategy model
uv run python -m agente_logistico.evaluacion_router --strategy hybrid

# Y el workflow con extracción en lenguaje natural:
uv run python -m agente_logistico --id-hilo demo-llm \
  --solicitud "Andes Manufactura (C-1003) necesita 6 EDGE-ORIN para el 2026-03-19"
```

## Estructura actual

```text
src/agente_logistico/
  config_caso.py       # Identidad y parámetros reproducibles del caso
  inicializar_datos.py # Esquema y datos sintéticos SQLite
  reglas.py            # Reglas deterministas del compromiso de entrega
  contratos.py         # Rutas y respuestas tipadas
  servicios.py         # Capa única de acceso a datos de dominio
  rag.py               # Índice local, caché, fuentes citables y embedder offline
  router.py            # Router determinista, por modelo e híbrido
  tools.py             # Tools semánticas, SQL y RAG
  orquestador.py       # Restricción de capacidades por ruta
  evaluacion_router.py # Benchmark de 12 casos
  calibracion_rag.py   # Calibración medible del umbral de abstención RAG
  estado_workflow.py   # Solicitud y estado tipado del grafo
  workflow.py          # Grafo LangGraph con retry, checkpoint e HITL
  reintento.py         # Retry con backoff para errores transitorios
  cli.py               # CLI del workflow (estructurado, natural o reanudación)
docs/
  politica_compromiso_entrega.md
  politica_despacho_extraordinario.md
  responsabilidades.md
  workflow.md
data/
  router_cases.json
tests/                 # Pruebas del escenario, RAG, SQL, tools, router y workflow
evidencias/            # Salidas reales de verificación
```

La ruta `WORKFLOW` ya ejecuta el grafo con estado; retry, checkpoint e HITL llegan en el Hito 04 y MCP en el Hito 05.

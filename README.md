# Agente logístico — LOG-001

Proyecto del Módulo 3 para evaluar compromisos de entrega B2B de AndesSupply.

- **Estudiante:** Marcelino Rafael Heredia Garcia
- **Variante:** Logística
- **Caso:** `LOG-001`
- **Semilla:** `6739`
- **Estado actual:** Hito 02, Router + RAG + SQL + Tools

La semilla determina la capacidad diaria, la ventana estándar de entrega y el costo del despacho extraordinario. Los datos son sintéticos y la fecha de referencia es fija para que las ejecuciones sean reproducibles.

## Requisitos

- Python 3.11 o superior
- [uv](https://docs.astral.sh/uv/)

Las pruebas y el router determinista no necesitan credenciales. Para ejecutar el router por modelo/híbrido o reconstruir el índice RAG real, copia `.env.example` como `.env` y configura `OPENAI_API_KEY`; el archivo `.env` no se versiona.

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

Resultados actuales: 54 pruebas verdes y 12/12 casos del router determinista.

`inicializar_datos` recrea únicamente la base sintética `data/logistica.db`. Esta base, `.env` y los entornos locales están excluidos de Git.

## Credenciales opcionales

```powershell
Copy-Item .env.example .env
```

Después de completar la clave en `.env`, pueden compararse las otras estrategias:

```bash
uv run python -m agente_logistico.evaluacion_router --strategy model
uv run python -m agente_logistico.evaluacion_router --strategy hybrid
```

## Estructura actual

```text
src/agente_logistico/
  config_caso.py       # Identidad y parámetros reproducibles del caso
  inicializar_datos.py # Esquema y datos sintéticos SQLite
  reglas.py            # Reglas deterministas del compromiso de entrega
  contratos.py         # Rutas y respuestas tipadas
  servicios.py         # Capa única de acceso a datos de dominio
  rag.py               # Índice local, caché y fuentes citables
  router.py            # Router determinista, por modelo e híbrido
  tools.py             # Tools semánticas, SQL y RAG
  orquestador.py       # Restricción de capacidades por ruta
  evaluacion_router.py # Benchmark de 12 casos
docs/
  politica_compromiso_entrega.md
  politica_despacho_extraordinario.md
  responsabilidades.md
data/
  router_cases.json
tests/                 # Pruebas del escenario, RAG, SQL, tools y router
evidencias/            # Salidas reales de verificación
```

La ruta `WORKFLOW` ya es reconocida por el router, pero su ejecución se implementará en el Hito 03. MCP pertenece al Hito 05.

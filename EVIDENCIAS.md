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

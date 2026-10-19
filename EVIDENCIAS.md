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

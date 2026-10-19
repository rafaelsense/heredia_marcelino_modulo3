# Separación de responsabilidades — Hito 01

## Escenario

El agente evaluará compromisos de entrega de AndesSupply para `LOG-001`. La fecha fija de referencia es `2026-03-16`. Con la semilla `6739`, la capacidad normal es de 6 unidades por día, la ventana estándar es de 3 días hábiles y el despacho extraordinario cuesta USD 400.

## Clasificación de solicitudes

| Consulta | Capacidad esperada | Justificación |
|---|---|---|
| ¿Cuál es la política para comprometer una fecha de entrega? | RAG | La respuesta debe recuperar y citar la política documental vigente, no inferirla desde datos transaccionales. |
| ¿Cuántas unidades de EDGE-ORIN vendimos a C-1003 durante el primer trimestre? | SQL parametrizado | Es una agregación exacta sobre ventas históricas con filtros por cliente, SKU y fechas. |
| ¿Qué stock disponible hay de EDGE-ORIN en ALM-LIM? | Tool `consultar_disponibilidad` | El stock es operacional y cambia con el tiempo; debe consultarse en la fuente transaccional. |
| ¿Qué capacidad de despacho queda para el 2026-03-18? | Tool `consultar_capacidad_despacho` | Debe combinar la capacidad configurada con las reservas de esa fecha y devolver un dato acotado. |
| C-1003 necesita 6 EDGE-ORIN para el 2026-03-19. Evalúa y confirma la entrega. | Workflow + Tools + reglas | Requiere extraer la solicitud, consultar datos, aplicar reglas y recorrer un proceso con estado; la confirmación no la decide el LLM. |
| C-1003 necesita 12 EDGE-ORIN para el siguiente día hábil. Evalúa la entrega. | Workflow + reglas + HITL | La capacidad normal es insuficiente, pero la extraordinaria es viable; el supervisor debe aprobar antes de confirmar. |
| Evalúa 40 EDGE-ORIN para C-1003 con entrega el 2026-03-19. | Workflow + regla de rechazo | El stock disponible es 30; repetir la consulta no cambiará el resultado y no corresponde retry. |
| Necesito una entrega urgente de equipos. | Aclaración | Faltan cliente, SKU, cantidad y fecha; ejecutar herramientas implicaría inventar datos esenciales. |
| ¿Qué diferencia hay entre despacho normal y extraordinario según la política interna? | RAG | Es una comparación de definiciones y condiciones documentales que exige fuentes. |
| ¿Qué significa SKU? | Respuesta directa | Es una definición general que no requiere datos internos, documentos ni herramientas. |

## Decisiones que no necesitan un LLM

- Comparar cantidad solicitada y stock disponible.
- Sumar días hábiles y comparar fechas.
- Calcular capacidad normal y extraordinaria disponible.
- Determinar si corresponde confirmación directa, aprobación o rechazo.
- Calcular el costo extraordinario a partir de los parámetros del caso.

El LLM se reservará para interpretar lenguaje natural, clasificar consultas cuando las reglas no sean suficientes y redactar respuestas con evidencia. Las ramas críticas utilizarán resultados tipados de las reglas.

## Datos que no deben vivir en un prompt

- Stock y reservas de capacidad, porque cambian con la operación.
- Clientes, productos y ventas históricas, porque deben consultarse con filtros y permanecer trazables.
- Capacidad diaria, ventana de entrega y costo extraordinario, porque dependen de la semilla y deben poder modificarse sin reescribir instrucciones.
- Credenciales y datos de conexión, que pertenecen a la configuración segura del entorno.

## Información documental frente a transaccional

La información **documental** describe políticas, definiciones, responsables y condiciones; se recuperará con RAG y citas en el Hito 02. La información **transaccional** representa el estado operativo o los hechos históricos; se consultará mediante SQL y tools tipadas. Una cita documental no reemplaza una consulta de stock y una fila SQLite no sustituye la política que explica una aprobación.

## Reglas iniciales del escenario

- Los días hábiles son de lunes a viernes; este escenario sintético no incorpora feriados.
- Una entrega directa exige stock suficiente, fecha igual o posterior a la ventana estándar y capacidad normal disponible.
- Un despacho extraordinario puede atenderse desde el siguiente día hábil y duplica la capacidad diaria, descontando las reservas existentes.
- Toda excepción viable queda pendiente de aprobación del supervisor y registra un costo de USD 400.
- Stock insuficiente, fecha pasada, entrega el mismo día o capacidad extraordinaria insuficiente producen rechazo de negocio, no retry.

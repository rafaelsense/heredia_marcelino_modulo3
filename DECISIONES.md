# Decisiones de ingeniería — LOG-001

Registro elaborado durante el desarrollo. Se ampliará en los hitos de workflow, robustez y MCP.

## 1. Router híbrido con cinco destinos

- **Problema:** elegir RAG, SQL, tools, workflow, aclaración o respuesta directa sin enviar cada consulta a todas las capacidades.
- **Alternativas:** solo reglas, solo LLM o invocar todas las tools y dejar que el modelo decida con los resultados.
- **Decisión:** reglas deterministas primero y modelo con salida estructurada únicamente cuando la confianza es baja.
- **Trade-off:** mayor mantenimiento de reglas y necesidad de evaluar el fallback, pero menor coste y comportamiento auditable para los casos frecuentes.
- **Riesgo:** vocabulario incompleto en las reglas; se demostró con “existencias” y se corrigió mediante los 12 casos.
- **En producción:** calibrar umbrales con datos reales, registrar decisiones incorrectas y revisar periódicamente las reglas.

## 2. RAG local con dos políticas, caché y abstención

- **Problema:** responder sobre políticas logísticas con fuentes sin mezclarlas con stock, capacidad o ventas.
- **Alternativas:** incrustar las políticas en el prompt, consultar siempre una base vectorial externa o tratar los documentos como texto libre sin citas.
- **Decisión:** indexar dos Markdown por secciones, usar embeddings, invalidar la caché por contenido/modelo y devolver `source_ref`; un score bajo produce ausencia de evidencia.
- **Trade-off:** dependencia del proveedor de embeddings para reconstruir el índice y menor escalabilidad que una base vectorial.
- **Riesgo:** confundir Top-K con relevancia o usar un índice obsoleto; se mitiga con umbral, fingerprint y pruebas de abstención. El umbral se calibra por modelo de embeddings con `calibracion_rag.py` (12 consultas etiquetadas, punto medio del hueco; con Gemini: 0.65, margen 0.059).
- **En producción:** usar una base vectorial administrada, versionado documental, evaluación de recuperación y control de acceso por documento.

## 3. SQL parametrizado como capacidad acotada

- **Problema:** obtener agregados históricos exactos sin permitir SQL libre generado por el modelo.
- **Alternativas:** exponer `ejecutar_sql(sql)`, resolver las consultas con RAG o incorporar un ORM completo.
- **Decisión:** una función concreta de resumen de ventas, fragmentos `WHERE` fijos y todos los valores como parámetros.
- **Trade-off:** menos flexibilidad para consultas nuevas, pero una superficie de seguridad mucho menor.
- **Riesgo:** creer que cualquier filtro dinámico es seguro; solo los valores son parametrizados y los nombres de campos permanecen fijos.
- **En producción:** usar credenciales de solo lectura, vistas o procedimientos aprobados, límites de resultado y auditoría.

## 4. Tools semánticas sobre una capa única de servicios

- **Problema:** exponer cliente, disponibilidad y capacidad sin duplicar lógica entre agente, workflow y MCP.
- **Alternativas:** una tool genérica, implementaciones separadas para cada consumidor o acceso directo a SQLite desde los prompts.
- **Decisión:** tres tools de negocio con argumentos tipados que delegan en `servicios.py` y devuelven errores homogéneos.
- **Trade-off:** se requiere una capa adicional, pero las validaciones y respuestas se prueban una sola vez.
- **Riesgo:** que las respuestas se vuelvan demasiado amplias o cambien sin versionarse.
- **En producción:** añadir autorización por capacidad, contratos versionados, métricas y adaptadores a ERP/WMS reales.

## 5. Fijación de versiones compatibles del SDK

- **Problema:** `openai-agents 0.24.0` y `0.0.19` fallaban al importarse con Python 3.11.0; además, `openai 3.35.1` era incompatible con el contexto de uso del SDK 0.0.17.
- **Alternativas:** actualizar Python, modificar internamente el SDK, ocultar el contexto en las pruebas o fijar versiones verificadas.
- **Decisión:** fijar `openai-agents==0.0.17` y `openai==2.9.0`, comprobadas mediante importación, creación de contexto y 54 pruebas.
- **Trade-off:** se usa una versión anterior del SDK y será necesario planificar una actualización controlada.
- **Riesgo:** perder correcciones recientes o encontrar incompatibilidades en hitos posteriores, especialmente MCP.
- **En producción:** mantener una matriz Python/SDK soportada, actualizar primero el runtime y validar todas las rutas antes de cambiar versiones.

## 6. Workflow LangGraph con dependencias inyectables

- **Problema:** orquestar extracción, datos operativos, capacidad, políticas y reglas sin esconder las ramas de negocio en una cadena `if/else`.
- **Alternativas:** una función secuencial con condicionales, un único agente con todas las tools o un grafo con estado tipado.
- **Decisión:** grafo LangGraph de nueve nodos con tres aristas condicionales, estado `EstadoLogistico` auditable y extractor, embedder y base de datos inyectables en `build_workflow`.
- **Trade-off:** más estructura que una función, pero las rutas quedan explícitas, dibujables y preparadas para retry, checkpoint e HITL del Hito 04.
- **Riesgo:** que el estado crezca con datos innecesarios; se mitiga con un contrato cerrado y una prueba que verifica sus campos.
- **En producción:** persistir el estado con un checkpointer duradero, registrar cada transición y versionar el grafo junto con las reglas.

## 7. Degradación documentada del nodo RAG sin credenciales

- **Problema:** ejecutar el workflow completo sin `OPENAI_API_KEY` sin falsear la recuperación semántica.
- **Alternativas:** abortar el flujo, simular fuentes o separar claramente la vía offline de la de producción.
- **Decisión:** el nodo `recuperar_politica` degrada con advertencia porque la decisión depende de reglas deterministas; para la demostración offline se añadió `embedder_lexico` con caché propia (`.cache/politicas_index_lexico.json`).
- **Trade-off:** el embedder léxico no es semántico; solo demuestra la mecánica del pipeline sin red.
- **Riesgo:** presentar la recuperación léxica como equivalente a la de OpenAI; los documentos y evidencias la identifican explícitamente como vía offline.
- **En producción:** esta vía no aplica; se usa el índice de embeddings del proveedor con su caché independiente.

## 8. Modelo Gemini más económico verificado con la clave real

- **Problema:** elegir el modelo Gemini de menor costo sin asumir que el catálogo público aplica a cualquier clave.
- **Alternativas:** `gemini-2.5-flash-lite` (el más barato del catálogo), `gemini-3.6-flash` (estable), `gemini-3.8-flash` (preview) y `gemini-3.5-flash-lite` (estable, económico).
- **Decisión:** `gemini-3.5-flash-lite` como modelo por defecto para Gemini, tras probar cada candidato con la clave real: `2.5-flash-lite` ya no está disponible para usuarios nuevos (404), `3.6-flash` agotó su cuota diaria del nivel gratuito (20 solicitudes/día) y `3.8-flash` respondió 503 por alta demanda.
- **Trade-off:** un modelo lite tiene menor capacidad de razonamiento; se mitiga manteniendo las decisiones de negocio en reglas deterministas y usando el LLM solo para clasificar y extraer.
- **Riesgo:** los límites del nivel gratuito (5 solicitudes/minuto) obligan a espaciar las evaluaciones (`--delay`); un cambio de modelo exige recalibrar el umbral RAG (`RAG_MIN_SCORE`).
- **En producción:** habilitar facturación, monitorear cuotas por modelo y fijar `MODEL_NAME` explícitamente en cada entorno.

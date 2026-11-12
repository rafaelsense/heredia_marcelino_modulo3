# Reflexión final — LOG-001 (Hito 06)

Reflexión crítica sobre el diseño del agente logístico, respondiendo las preguntas de la guía del Hito 06 y documentando limitaciones y riesgos reales del sistema entregado.

## Arquitectura integrada

```text
Solicitud (natural o estructurada)
   │
   ▼
Router (determinista / modelo / híbrido) ── destinos: RAG, SQL, TOOLS, WORKFLOW, CLARIFY, DIRECT
   │
   ├── RAG ──────► índice local de 2 políticas, fuentes citables, abstención calibrada (0.65)
   ├── SQL ──────► consultas parametrizadas sobre ventas (servicios.py)
   ├── TOOLS ────► consultar_cliente / consultar_disponibilidad / consultar_capacidad_despacho
   └── WORKFLOW ─► LangGraph (10 nodos, 4 aristas condicionales)
                     ├─ extracción (LLM o estructurada)
                     ├─ datos operativos (cliente, SKU, stock)   ← SQL parametrizado
                     ├─ capacidad de despacho                     ← tool con retry transitorio
                     ├─ política de compromiso                    ← RAG con fuentes
                     ├─ reglas deterministas (Python puro)        ← la decisión NO es del LLM
                     ├─ directo / excepción / rechazo / aclaración
                     └─ HITL: interrupt() + checkpoint SQLite + reanudación por id_hilo

Capa de servicios expuesta además por MCP stdio (4 tools, 2 recursos, 1 prompt)
para que otros consumidores la usen sin acoplarse a este agente.
```

## ¿Qué parte es probabilística y qué parte determinista?

- **Determinista (Python):** los parámetros de la semilla, todas las reglas del compromiso de entrega (ventana estándar, capacidad diaria, costo extraordinario, rechazos de negocio), el SQL, la composición de la respuesta final y el router en modo determinista/híbrido. Estas partes son auditables y se repiten idénticamente con la misma entrada.
- **Probabilística (LLM):** la interpretación de lenguaje natural (extracción de cliente/SKU/cantidad/fecha y clasificación de ruta en la estrategia `model`) y los embeddings del índice RAG.
- **Frontera defendida:** el LLM *propone* datos; las reglas *deciden*. Un compromiso de entrega nunca se confirma porque el modelo lo afirme: se confirma porque `reglas.py` lo valida contra la base. Los outputs del LLM pasan por validación Pydantic antes de tocar el grafo, y el modo `hybrid` hace que el router por modelo solo opere cuando el vocabulario determinista no decide, con las tools ya restringidas por ruta.

## ¿Qué cambiaría si operara con SAP/ERP/CRM reales?

- `servicios.py` dejaría de leer SQLite y pasaría a clientes de API/OData con contratos de error equivalentes (`ok`, `error_type`, `recoverable`); el resto del sistema no debería enterarse, porque todas las rutas consumen esa capa (esa fue justamente la decisión 4 y 11 de `DECISIONES.md`).
- El retry transitorio se volvería indispensable de verdad (hoy se demuestra con un fallo simulado) y habría que añadir timeouts, circuit breaker e idempotency keys para las escrituras.
- El HITL necesitaría una bandeja de aprobaciones real (cola + identidad del supervisor autenticada) en lugar de la CLI; el checkpoint pasaría de SQLite a un almacén compartido (Postgres/Redis) para sobrevivir a réplicas.
- RAG indexaría las políticas desde su fuente documental oficial (SharePoint/GED) con versionado, y el índice se movería a una base vectorial externa.

## ¿Cuál es el mayor riesgo del diseño actual?

La **extracción de lenguaje natural**: un campo mal extraído (p. ej. cantidad 6 confundida con 60) llega validado sintácticamente pero errado semánticamente, y el sistema podría confirmar un compromiso equivocado. Las mitigaciones actuales son la validación Pydantic, la trazabilidad con fuentes y que el caso urgente termina en aprobación humana; pero el camino directo confía en la extracción. En producción añadiría una confirmación de los datos interpretados antes de evaluar reglas (un nodo de "confirmar entendimiento" barato), o restringiría el lenguaje natural a redactar la respuesta y mantendría la entrada estructurada.

## ¿Qué simplificaría si tuviera que mantenerlo un año?

- El router quedaría en una sola estrategia (la híbrida) en lugar de tres: mantener tres evaluadores y sus evidencias cuesta más de lo que aporta fuera del contexto formativo.
- El embedder léxico offline desaparecería: existe para demostrar sin credenciales, pero duplica la caché del índice y es una superficie de mantenimiento que en producción no se justifica.
- Los `hooks` de simulación de fallo se extraerían a un arnés de pruebas, fuera del código de producción.

## Limitaciones reales declaradas

1. **Agente→MCP con Gemini 3.x:** el SDK `openai-agents==0.0.17` no preserva `thought_signature` en el segundo turno de tools (verificado con HTTP directo). La capacidad MCP se verifica con el cliente puro; la vía agente→MCP funciona con el proveedor OpenAI. Detalle en `DECISIONES.md` (11) y `evidencias/hito05_agente_mcp.log`.
2. **Nivel gratuito de Gemini:** 5 solicitudes/minuto y cuotas diarias por modelo; por eso el evaluador del router usa `--delay` y las evidencias masivas se generaron en modo offline/determinista.
3. **Umbral RAG por proveedor:** 0.65 está calibrado con `gemini-embedding-001` y los dos documentos actuales; con otro proveedor o más documentos debe recalibrarse (`calibracion_rag.py`).
4. **Pins de versiones:** `openai-agents==0.0.17` y `openai==2.9.0` son la combinación verificada con Python 3.11.0; actualizar exige re-verificar importación y creación de contexto.
5. **Datos sintéticos:** clientes, inventario y ventas son de demostración; las reglas son las que importan y están parametrizadas por la semilla.

## Aprendizaje central

La pregunta guía del proyecto —cómo hacer útil al LLM sin hacerlo responsable de todo— se respondió con una frontera clara: el modelo interpreta y clasifica; el código decide y ejecuta; el humano resuelve las excepciones. Cada tecnología está donde está por una razón comprobable, y las que fallaron (versiones, modelos, thought signatures) quedaron documentadas con su evidencia en lugar de ocultarse.

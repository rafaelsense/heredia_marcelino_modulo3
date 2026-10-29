"""Orquestador inicial que restringe las capacidades según la ruta elegida."""

import sys
import uuid
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStdio, MCPServerStdioParams

from .contratos import AppContext, FinalAnswer, Route, RouteDecision
from .modelo import build_model
from .router import DeterministicRouter, HybridRouter, ModelRouter
from .tools import TOOLS_RAG, TOOLS_SEMANTICAS, TOOLS_SQL

RUTA_SERVIDOR_MCP = Path(__file__).resolve().parent / "servidor_mcp.py"
RUTAS_CON_MCP = (Route.SQL, Route.TOOLS)


def _tools_for(route: Route) -> list:
    """Reduce la superficie de tools disponible para cada destino."""
    if route == Route.RAG:
        return TOOLS_RAG
    if route == Route.SQL:
        return TOOLS_SQL
    if route == Route.TOOLS:
        return TOOLS_SEMANTICAS
    return []


def _instructions_for(route: Route) -> str:
    """Define instrucciones acotadas sin convertir al LLM en regla de negocio."""
    base = (
        "Eres el agente de operaciones logísticas LOG-001. No inventes datos internos. "
        "Usa solo las tools habilitadas en esta ejecución y separa hechos de advertencias. "
        "Si la evidencia es insuficiente, dilo explícitamente."
    )
    if route == Route.RAG:
        return base + " Sustenta la respuesta en los fragmentos recuperados y cita sus source_ref."
    if route == Route.SQL:
        return base + " Responde con los agregados históricos y cita la fuente SQL devuelta."
    if route == Route.TOOLS:
        return base + " Responde con el dato operacional actual y no confirmes compromisos."
    return base + " Responde conceptualmente sin afirmar datos internos."


async def choose_route(query: str, strategy: str = "deterministic") -> RouteDecision:
    """Selecciona la estrategia de router configurada para la consulta."""
    if strategy == "deterministic":
        return DeterministicRouter().route(query)
    if strategy == "model":
        return await ModelRouter().route(query)
    if strategy == "hybrid":
        return await HybridRouter().route(query)
    raise ValueError(f"Estrategia de router no soportada: {strategy}")


async def answer(
    query: str, strategy: str = "deterministic", usar_mcp: bool = False
) -> tuple[RouteDecision, FinalAnswer]:
    """Ejecuta la ruta elegida sin exponer herramientas fuera de su alcance.

    Con `usar_mcp=True`, las rutas SQL y TOOLS consumen las capacidades desde
    el servidor MCP (proceso separado) en lugar de las tools locales; la ruta
    RAG sigue local porque el servidor expone las políticas como recursos.

    Limitación conocida: con Gemini 3.x la continuación multi-turno de tools
    exige `thought_signature`, que el pin `openai-agents==0.0.17` no preserva;
    con el proveedor OpenAI esta vía funciona completa. La capacidad MCP se
    verifica de forma independiente en `cliente_mcp.py` y `tests/test_mcp.py`.
    """
    decision = await choose_route(query, strategy)
    if decision.route == Route.CLARIFY:
        return decision, FinalAnswer(
            answer=decision.clarification_question or "Necesito más información.",
            warnings=[decision.reason],
        )
    if decision.route == Route.WORKFLOW:
        return decision, FinalAnswer(
            answer="La solicitud corresponde al workflow de compromiso de entrega.",
            warnings=[
                "Ejecútalo con: python -m agente_logistico "
                "(--cliente --sku --cantidad --fecha, o --solicitud con API)."
            ],
        )

    if usar_mcp and decision.route in RUTAS_CON_MCP:
        params = MCPServerStdioParams(
            command=sys.executable, args=[str(RUTA_SERVIDOR_MCP)]
        )
        async with MCPServerStdio(params, name="logistica-log001") as servidor:
            agent = Agent[AppContext](
                name="Agente Logístico LOG-001",
                model=build_model(),
                instructions=_instructions_for(decision.route),
                mcp_servers=[servidor],
                output_type=FinalAnswer,
            )
            resultado = await Runner.run(
                agent, query, context=AppContext(request_id=str(uuid.uuid4()))
            )
        return decision, resultado.final_output

    agent = Agent[AppContext](
        name="Agente Logístico LOG-001",
        model=build_model(),
        instructions=_instructions_for(decision.route),
        tools=_tools_for(decision.route),
        output_type=FinalAnswer,
    )
    resultado = await Runner.run(
        agent,
        query,
        context=AppContext(request_id=str(uuid.uuid4())),
    )
    return decision, resultado.final_output

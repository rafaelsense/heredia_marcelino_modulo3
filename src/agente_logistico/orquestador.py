"""Orquestador inicial que restringe las capacidades según la ruta elegida."""

import uuid

from agents import Agent, Runner

from .contratos import AppContext, FinalAnswer, Route, RouteDecision
from .modelo import build_model
from .router import DeterministicRouter, HybridRouter, ModelRouter
from .tools import TOOLS_RAG, TOOLS_SEMANTICAS, TOOLS_SQL


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


async def answer(query: str, strategy: str = "deterministic") -> tuple[RouteDecision, FinalAnswer]:
    """Ejecuta la ruta elegida sin exponer herramientas fuera de su alcance."""
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

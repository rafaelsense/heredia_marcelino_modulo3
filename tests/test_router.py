import asyncio
import json
from pathlib import Path

import pytest

from agente_logistico.contratos import Route
from agente_logistico.orquestador import answer
from agente_logistico.router import DeterministicRouter

CASOS = json.loads(
    (Path(__file__).parents[1] / "data" / "router_cases.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("caso", CASOS, ids=[caso["q"] for caso in CASOS])
def test_router_deterministico_clasifica_los_12_casos(caso):
    assert DeterministicRouter().route(caso["q"]).route.value == caso["expected"]


def test_consulta_ambigua_se_aclara_sin_agente_ni_tools():
    decision, respuesta = asyncio.run(answer("Necesito una entrega urgente de equipos."))

    assert decision.route == Route.CLARIFY
    assert decision.confidence == 0.55
    assert respuesta.answer == decision.clarification_question
    assert respuesta.facts == []


def test_ruta_workflow_queda_identificada_sin_simular_el_hito03():
    decision, respuesta = asyncio.run(
        answer("Evalúa y confirma 6 EDGE-ORIN para C-1003 con entrega el 2026-03-19.")
    )

    assert decision.route == Route.WORKFLOW
    assert "Hito 03" in respuesta.warnings[0]

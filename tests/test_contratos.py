import pytest
from pydantic import ValidationError

from agente_logistico.contratos import Route, RouteDecision


def test_route_decision_valida_confianza():
    decision = RouteDecision(route=Route.RAG, confidence=0.95, reason="Documental")

    assert decision.route == Route.RAG
    assert decision.clarification_question is None


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_route_decision_rechaza_confianza_fuera_de_rango(confidence):
    with pytest.raises(ValidationError):
        RouteDecision(route=Route.SQL, confidence=confidence, reason="Inválida")

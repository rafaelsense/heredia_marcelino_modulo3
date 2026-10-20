"""Contratos tipados compartidos por router, tools y orquestador."""

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Route(str, Enum):
    """Destinos permitidos para una consulta del agente logístico."""

    RAG = "rag"
    SQL = "sql"
    TOOLS = "tools"
    WORKFLOW = "workflow"
    CLARIFY = "clarify"
    DIRECT = "direct"


class RouteDecision(BaseModel):
    """Decisión estructurada del router con trazabilidad de su motivo."""

    model_config = ConfigDict(extra="forbid")

    route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    clarification_question: str | None = None


class FinalAnswer(BaseModel):
    """Respuesta final separada en conclusión, hechos, advertencias y fuentes."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    facts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class AppContext:
    """Contexto mínimo disponible para las tools durante una ejecución."""

    request_id: str

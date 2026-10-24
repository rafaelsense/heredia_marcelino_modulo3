"""Contratos de estado para el workflow LangGraph de compromisos de entrega."""

import operator
from datetime import date
from enum import Enum
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SolicitudLogistica(BaseModel):
    """Solicitud de compromiso ya estructurada y validada antes de evaluar reglas."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    fecha_entrega: date
    almacen: str = "ALM-LIM"

    @field_validator("cliente_id", "sku", "almacen")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        """Uniforma los identificadores para coincidir con la base operativa."""
        return valor.strip().upper()


class EstadoProceso(str, Enum):
    """Resultados terminales o intermedios posibles del workflow."""

    PROCESANDO = "procesando"
    ACLARACION = "aclaracion"
    CONFIRMADO = "confirmado"
    PENDIENTE_APROBACION = "pendiente_aprobacion"
    RECHAZADO = "rechazado"


class EstadoLogistico(TypedDict, total=False):
    """Estado del grafo: solo datos necesarios para decidir y auditar el caso.

    No guarda claves, conexiones, historial conversacional ni documentos crudos.
    `fuentes` acumula referencias citables con un reductor aditivo.
    """

    caso_id: str
    semilla: int
    id_solicitud: str
    solicitud_original: str
    solicitud: dict[str, Any] | None
    cliente: dict[str, Any] | None
    stock_disponible: int | None
    capacidad: dict[str, Any] | None
    evaluacion: dict[str, Any] | None
    fuentes: Annotated[list[str], operator.add]
    aprobacion: dict[str, Any] | None
    estado: str
    mensaje: str


def estado_inicial(solicitud_original: str, id_solicitud: str) -> EstadoLogistico:
    """Crea el estado de entrada con la identidad trazable del escenario."""
    from .config_caso import CASO_ID, SEMILLA

    return EstadoLogistico(
        caso_id=CASO_ID,
        semilla=SEMILLA,
        id_solicitud=id_solicitud,
        solicitud_original=solicitud_original,
        solicitud=None,
        cliente=None,
        stock_disponible=None,
        capacidad=None,
        evaluacion=None,
        fuentes=[],
        aprobacion=None,
        estado=EstadoProceso.PROCESANDO.value,
        mensaje="",
    )

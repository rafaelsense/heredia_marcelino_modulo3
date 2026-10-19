"""Reglas deterministas para evaluar compromisos de entrega sin usar un LLM."""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum


class DecisionCompromiso(str, Enum):
    """Decisiones de negocio permitidas para una solicitud de entrega."""

    DIRECTO = "directo"
    REQUIERE_APROBACION = "requiere_aprobacion"
    RECHAZADO = "rechazado"


class TipoDespacho(str, Enum):
    """Modalidad de despacho asociada a la decisión evaluada."""

    NORMAL = "normal"
    EXTRAORDINARIO = "extraordinario"
    NO_VIABLE = "no_viable"


@dataclass(frozen=True)
class EvaluacionCompromiso:
    """Resultado tipado y trazable de las reglas de compromiso de entrega."""

    decision: DecisionCompromiso
    tipo_despacho: TipoDespacho
    motivo: str
    costo_extraordinario_usd: int
    fecha_minima_normal: date
    capacidad_normal_disponible: int
    capacidad_extraordinaria_disponible: int


def sumar_dias_habiles(fecha: date, dias: int) -> date:
    """Suma días de lunes a viernes; este escenario no considera feriados."""
    if dias < 0:
        raise ValueError("Los días hábiles no pueden ser negativos")
    resultado = fecha
    agregados = 0
    while agregados < dias:
        resultado += timedelta(days=1)
        if resultado.weekday() < 5:
            agregados += 1
    return resultado


def evaluar_compromiso(
    *,
    fecha_solicitud: date,
    fecha_entrega: date,
    cantidad: int,
    stock_disponible: int,
    capacidad_diaria: int,
    capacidad_reservada: int,
    ventana_entrega_dias: int,
    costo_extraordinario_usd: int,
) -> EvaluacionCompromiso:
    """Decide entre entrega directa, aprobación extraordinaria o rechazo de negocio."""
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")
    if stock_disponible < 0:
        raise ValueError("El stock disponible no puede ser negativo")
    if capacidad_diaria <= 0:
        raise ValueError("La capacidad diaria debe ser mayor que cero")
    if capacidad_reservada < 0:
        raise ValueError("La capacidad reservada no puede ser negativa")
    if ventana_entrega_dias <= 0:
        raise ValueError("La ventana de entrega debe ser mayor que cero")
    if costo_extraordinario_usd < 0:
        raise ValueError("El costo extraordinario no puede ser negativo")

    fecha_minima_normal = sumar_dias_habiles(fecha_solicitud, ventana_entrega_dias)
    capacidad_normal = max(capacidad_diaria - capacidad_reservada, 0)
    capacidad_extraordinaria = max(capacidad_diaria * 2 - capacidad_reservada, 0)

    def evaluacion(
        decision: DecisionCompromiso,
        tipo: TipoDespacho,
        motivo: str,
        costo: int = 0,
    ) -> EvaluacionCompromiso:
        """Crea un resultado con las métricas comunes a todas las ramas."""
        return EvaluacionCompromiso(
            decision=decision,
            tipo_despacho=tipo,
            motivo=motivo,
            costo_extraordinario_usd=costo,
            fecha_minima_normal=fecha_minima_normal,
            capacidad_normal_disponible=capacidad_normal,
            capacidad_extraordinaria_disponible=capacidad_extraordinaria,
        )

    if cantidad > stock_disponible:
        return evaluacion(
            DecisionCompromiso.RECHAZADO,
            TipoDespacho.NO_VIABLE,
            f"Stock insuficiente: solicitadas {cantidad}, disponibles {stock_disponible}.",
        )
    if fecha_entrega < fecha_solicitud:
        return evaluacion(
            DecisionCompromiso.RECHAZADO,
            TipoDespacho.NO_VIABLE,
            "La fecha de entrega es anterior a la fecha de solicitud.",
        )
    if fecha_entrega >= fecha_minima_normal and cantidad <= capacidad_normal:
        return evaluacion(
            DecisionCompromiso.DIRECTO,
            TipoDespacho.NORMAL,
            "Entrega viable con capacidad y ventana estándar.",
        )

    fecha_minima_extraordinaria = sumar_dias_habiles(fecha_solicitud, 1)
    if fecha_entrega < fecha_minima_extraordinaria:
        return evaluacion(
            DecisionCompromiso.RECHAZADO,
            TipoDespacho.NO_VIABLE,
            "La fecha es anterior al siguiente día hábil; no es viable ni con despacho extraordinario.",
        )
    if cantidad <= capacidad_extraordinaria:
        return evaluacion(
            DecisionCompromiso.REQUIERE_APROBACION,
            TipoDespacho.EXTRAORDINARIO,
            "Requiere despacho extraordinario y aprobación del supervisor de logística.",
            costo_extraordinario_usd,
        )
    return evaluacion(
        DecisionCompromiso.RECHAZADO,
        TipoDespacho.NO_VIABLE,
        "Capacidad insuficiente incluso con despacho extraordinario: "
        f"disponibles {capacidad_extraordinaria}.",
    )

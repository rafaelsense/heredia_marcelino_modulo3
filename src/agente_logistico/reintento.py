"""Reintentos con backoff exponencial para fallos transitorios del agente.

Justificación real: durante la integración con Gemini se observaron errores
429 (cuota por minuto) y 503 (alta demanda) que se resolvían reintentando.
Los errores de negocio (stock insuficiente, cliente bloqueado) nunca se
reintentan: los rechazan las reglas deterministas sin pasar por aquí.
"""

import asyncio
import os
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from openai import APIConnectionError, InternalServerError, RateLimitError

T = TypeVar("T")


class ErrorTransitorioSimulado(Exception):
    """Fallo transitorio inyectado para demostrar el retry sin gastar cuota."""


TRANSITORIOS = (
    RateLimitError,          # 429: cuota por minuto del proveedor
    InternalServerError,     # 503: alta demanda temporal del modelo
    APIConnectionError,      # red o DNS transitorio
    ErrorTransitorioSimulado,
)

_fallos_simulados: set[str] = set()


def simular_fallo_transitorio(clave: str) -> None:
    """Falla una sola vez por clave si SIMULAR_FALLO_TRANSITORIO_CAPACIDAD=1.

    Permite evidenciar el retry de forma determinista y sin costo de API:
    la primera llamada con cada clave falla y las siguientes pasan.
    """
    if os.getenv("SIMULAR_FALLO_TRANSITORIO_CAPACIDAD") != "1":
        return
    if clave not in _fallos_simulados:
        _fallos_simulados.add(clave)
        raise ErrorTransitorioSimulado(
            f"Fallo transitorio simulado de capacidad para {clave}"
        )


def _espera(intento: int, espera_inicial: float, factor: float, jitter: float) -> float:
    """Backoff exponencial con jitter para evitar reintentos sincronizados."""
    return espera_inicial * factor ** (intento - 1) + random.uniform(0, jitter)


def con_reintento(
    funcion: Callable[[], T],
    *,
    intentos: int = 3,
    espera_inicial: float = 1.0,
    factor: float = 2.0,
    jitter: float = 0.2,
    descripcion: str = "operación",
) -> T:
    """Reintenta una operación síncrona solo ante errores transitorios."""
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TRANSITORIOS as exc:
            if intento == intentos:
                raise
            espera = _espera(intento, espera_inicial, factor, jitter)
            print(
                f"[retry] {descripcion}: intento {intento}/{intentos} falló "
                f"({type(exc).__name__}); reintento en {espera:.1f}s"
            )
            time.sleep(espera)
    raise AssertionError("inalcanzable")


async def acon_reintento(
    funcion: Callable[[], Awaitable[T]],
    *,
    intentos: int = 3,
    espera_inicial: float = 1.0,
    factor: float = 2.0,
    jitter: float = 0.2,
    descripcion: str = "operación",
) -> T:
    """Reintenta una operación asíncrona solo ante errores transitorios."""
    for intento in range(1, intentos + 1):
        try:
            return await funcion()
        except TRANSITORIOS as exc:
            if intento == intentos:
                raise
            espera = _espera(intento, espera_inicial, factor, jitter)
            print(
                f"[retry] {descripcion}: intento {intento}/{intentos} falló "
                f"({type(exc).__name__}); reintento en {espera:.1f}s"
            )
            await asyncio.sleep(espera)
    raise AssertionError("inalcanzable")

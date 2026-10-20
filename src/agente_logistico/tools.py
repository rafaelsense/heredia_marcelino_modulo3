"""Tools semánticas acotadas para el agente logístico LOG-001."""

import asyncio

from agents import RunContextWrapper, function_tool

from . import servicios
from .contratos import AppContext
from .rag import search as buscar_rag


@function_tool
async def consultar_cliente(ctx: RunContextWrapper[AppContext], cliente_id: str) -> dict:
    """Consulta el estado logístico actual de un cliente por identificador."""
    await asyncio.sleep(0)
    return servicios.consultar_cliente(cliente_id)


@function_tool
async def consultar_disponibilidad(
    ctx: RunContextWrapper[AppContext],
    sku: str,
    cantidad: int,
) -> dict:
    """Compara el stock disponible de un SKU con la cantidad solicitada."""
    await asyncio.sleep(0)
    return servicios.consultar_disponibilidad(sku, cantidad)


@function_tool
async def consultar_capacidad_despacho(
    ctx: RunContextWrapper[AppContext],
    fecha: str,
    cantidad: int,
    almacen: str = "ALM-LIM",
) -> dict:
    """Consulta la capacidad normal y extraordinaria disponible en una fecha."""
    await asyncio.sleep(0)
    return servicios.consultar_capacidad_despacho(fecha, cantidad, almacen)


@function_tool
async def resumen_ventas(
    ctx: RunContextWrapper[AppContext],
    sku: str | None = None,
    cliente_id: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> dict:
    """Resume ventas históricas mediante SQL parametrizado y filtros acotados."""
    await asyncio.sleep(0)
    return servicios.resumen_ventas(sku, cliente_id, fecha_desde, fecha_hasta)


@function_tool
async def buscar_politicas_logisticas(
    ctx: RunContextWrapper[AppContext],
    query: str,
    top_k: int = 3,
) -> dict:
    """Recupera políticas logísticas relevantes con fuentes citables."""
    await asyncio.sleep(0)
    resultados = buscar_rag(query, top_k)
    return {
        "ok": True,
        "query": query,
        "results": resultados,
        "evidencia_suficiente": bool(resultados),
        "source_ref": "[RAG:politicas]",
    }


TOOLS_SEMANTICAS = [consultar_cliente, consultar_disponibilidad, consultar_capacidad_despacho]
TOOLS_SQL = [resumen_ventas]
TOOLS_RAG = [buscar_politicas_logisticas]
TOOLS = [*TOOLS_SEMANTICAS, *TOOLS_SQL, *TOOLS_RAG]

"""Servidor MCP stdio que expone las capacidades logísticas desacopladas.

Las tools delegan en `servicios.py`, la misma capa que usan el agente y el
workflow: el servidor no duplica lógica de negocio, solo la expone por MCP.
Nota: se usa FastMCP de `mcp` 1.x porque el pin `openai-agents==0.0.17`
(Python 3.11.0) exige `mcp<2`
"""

import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Permite `python servidor_mcp.py` y ejecución como script desde MCP.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agente_logistico import servicios  # noqa: E402
from agente_logistico.rag import DOCS_DIR  # noqa: E402

mcp = FastMCP(
    "Logística LOG-001",
    instructions=(
        "Servidor MCP del caso LOG-001. Expone capacidades acotadas: clientes, "
        "disponibilidad de stock, capacidad de despacho, ventas históricas y "
        "políticas logísticas internas."
    ),
)


@mcp.tool()
def consultar_cliente(cliente_id: str) -> dict:
    """Obtiene el estado logístico de un cliente sin modificar la base."""
    return servicios.consultar_cliente(cliente_id)


@mcp.tool()
def consultar_disponibilidad(sku: str, cantidad: int) -> dict:
    """Compara el stock actual con una cantidad solicitada."""
    return servicios.consultar_disponibilidad(sku, cantidad)


@mcp.tool()
def consultar_capacidad_despacho(
    fecha: str, cantidad: int, almacen: str = "ALM-LIM"
) -> dict:
    """Calcula capacidad normal y extraordinaria disponible para una fecha."""
    return servicios.consultar_capacidad_despacho(fecha, cantidad, almacen)


@mcp.tool()
def resumen_ventas(
    sku: str | None = None,
    cliente_id: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> dict:
    """Resume ventas históricas con filtros fijos y valores parametrizados."""
    return servicios.resumen_ventas(sku, cliente_id, fecha_desde, fecha_hasta)


@mcp.resource("politica://compromiso-entrega", mime_type="text/markdown")
def politica_compromiso() -> str:
    """Política vigente de compromiso de entrega."""
    return (DOCS_DIR / "politica_compromiso_entrega.md").read_text(encoding="utf-8")


@mcp.resource("politica://despacho-extraordinario", mime_type="text/markdown")
def politica_extraordinario() -> str:
    """Política vigente de despacho extraordinario."""
    return (DOCS_DIR / "politica_despacho_extraordinario.md").read_text(
        encoding="utf-8"
    )


@mcp.prompt()
def evaluar_compromiso(cliente_id: str, sku: str, cantidad: str, fecha: str) -> str:
    """Prompt reutilizable para revisar un compromiso de entrega."""
    return (
        "Evalúa esta solicitud de compromiso de entrega LOG-001. "
        f"Cliente={cliente_id}, SKU={sku}, cantidad={cantidad}, fecha={fecha}. "
        "Verifica cliente, stock y capacidad con las herramientas disponibles. "
        "No inventes datos, no confirmes compromisos y separa hechos de advertencias."
    )


if __name__ == "__main__":
    # stdio es el transporte local por defecto del SDK MCP.
    mcp.run()

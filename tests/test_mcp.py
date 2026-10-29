"""Pruebas del Hito 05: servidor MCP stdio desacoplado del agente."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agente_logistico.inicializar_datos import inicializar_bd

RUTA_SERVIDOR = (
    Path(__file__).resolve().parents[1] / "src" / "agente_logistico" / "servidor_mcp.py"
)


def _texto(contenido) -> str:
    """Extrae el texto de un contenido MCP devuelto por el servidor."""
    partes = contenido if isinstance(contenido, list) else [contenido]
    return "\n".join(
        getattr(parte, "text", "") for parte in partes if getattr(parte, "text", None)
    )


async def _conectar(operacion):
    """Levanta el servidor como proceso separado y ejecuta la operación."""
    inicializar_bd()  # base sintética real, la misma que usa el servidor
    parametros = StdioServerParameters(
        command=sys.executable, args=[str(RUTA_SERVIDOR)]
    )
    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()
            return await operacion(sesion)


def test_servidor_expone_cuatro_tools_recursos_y_prompt():
    async def operacion(sesion):
        herramientas = await sesion.list_tools()
        recursos = await sesion.list_resources()
        prompts = await sesion.list_prompts()
        return herramientas, recursos, prompts

    herramientas, recursos, prompts = asyncio.run(_conectar(operacion))

    nombres = {herramienta.name for herramienta in herramientas.tools}
    assert nombres == {
        "consultar_cliente",
        "consultar_disponibilidad",
        "consultar_capacidad_despacho",
        "resumen_ventas",
    }
    uris = {str(recurso.uri) for recurso in recursos.resources}
    assert "politica://compromiso-entrega" in uris
    assert "politica://despacho-extraordinario" in uris
    assert {prompt.name for prompt in prompts.prompts} == {"evaluar_compromiso"}


def test_tool_mcp_disponibilidad_stock_insuficiente():
    async def operacion(sesion):
        resultado = await sesion.call_tool(
            "consultar_disponibilidad", {"sku": "EDGE-ORIN", "cantidad": 40}
        )
        return json.loads(_texto(resultado.content))

    datos = asyncio.run(_conectar(operacion))

    assert datos["ok"] is True
    assert datos["stock_disponible"] == 30
    assert datos["suficiente"] is False
    assert datos["source_ref"] == "[SQL:inventario]"


def test_tool_mcp_trata_inyeccion_como_parametro():
    async def operacion(sesion):
        resultado = await sesion.call_tool(
            "resumen_ventas", {"sku": "EDGE-ORIN' OR 1=1 --"}
        )
        return json.loads(_texto(resultado.content))

    datos = asyncio.run(_conectar(operacion))

    assert datos["ok"] is True
    assert datos["transacciones"] == 0


def test_recurso_mcp_devuelve_la_politica():
    async def operacion(sesion):
        recurso = await sesion.read_resource("politica://compromiso-entrega")
        return _texto(recurso.contents)

    texto = asyncio.run(_conectar(operacion))

    assert "ventana" in texto.lower()


def test_prompt_mcp_renderiza_con_argumentos():
    async def operacion(sesion):
        renderizado = await sesion.get_prompt(
            "evaluar_compromiso",
            arguments={
                "cliente_id": "C-1004",
                "sku": "EDGE-ORIN",
                "cantidad": "12",
                "fecha": "2026-03-17",
            },
        )
        return _texto([mensaje.content for mensaje in renderizado.messages])

    texto = asyncio.run(_conectar(operacion))

    assert "C-1004" in texto
    assert "EDGE-ORIN" in texto
    assert "no confirmes" in texto.lower() or "No inventes" in texto

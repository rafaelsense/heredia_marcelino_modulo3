import asyncio
import json

from agents import RunContextWrapper

from agente_logistico.contratos import AppContext
from agente_logistico.tools import (
    TOOLS_SEMANTICAS,
    consultar_capacidad_despacho,
    consultar_cliente,
    consultar_disponibilidad,
)


def invocar(tool, argumentos: dict):
    """Ejecuta una tool con el mismo contexto estructurado usado por el agente."""
    argumentos_json = json.dumps(argumentos)
    contexto = RunContextWrapper(AppContext("test-hito02"))
    return asyncio.run(tool.on_invoke_tool(contexto, argumentos_json))


def test_hay_tres_tools_semanticas_documentadas():
    assert len(TOOLS_SEMANTICAS) == 3
    assert all(tool.description for tool in TOOLS_SEMANTICAS)


def test_tool_consultar_cliente(bd_temporal):
    resultado = invocar(consultar_cliente, {"cliente_id": "C-1003"})

    assert resultado["ok"] is True
    assert resultado["cliente"]["cliente_id"] == "C-1003"


def test_tool_consultar_disponibilidad(bd_temporal):
    resultado = invocar(
        consultar_disponibilidad,
        {"sku": "EDGE-ORIN", "cantidad": 40},
    )

    assert resultado["ok"] is True
    assert resultado["suficiente"] is False


def test_tool_consultar_capacidad(bd_temporal):
    resultado = invocar(
        consultar_capacidad_despacho,
        {"fecha": "2026-03-17", "cantidad": 12},
    )

    assert resultado["ok"] is True
    assert resultado["suficiente_extraordinaria"] is True

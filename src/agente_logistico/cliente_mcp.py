"""Cliente MCP de demostración: recorre tools, recursos y prompts del servidor."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

RUTA_SERVIDOR = Path(__file__).resolve().parent / "servidor_mcp.py"


def _texto(contenido) -> str:
    """Extrae el texto de un contenido MCP devuelto por el servidor."""
    partes = contenido if isinstance(contenido, list) else [contenido]
    return "\n".join(
        getattr(parte, "text", "") for parte in partes if getattr(parte, "text", None)
    )


async def principal() -> None:
    """Conecta por stdio y ejercita cada capacidad expuesta."""
    parametros = StdioServerParameters(
        command=sys.executable, args=[str(RUTA_SERVIDOR)]
    )
    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            inicializacion = await sesion.initialize()
            print("=== CONEXIÓN MCP ===")
            print("servidor:", inicializacion.serverInfo.name)

            herramientas = await sesion.list_tools()
            print("\n=== HERRAMIENTAS ===")
            for herramienta in herramientas.tools:
                print(f"- {herramienta.name}: {herramienta.description}")

            for nombre, argumentos in [
                ("consultar_cliente", {"cliente_id": "C-1003"}),
                ("consultar_disponibilidad", {"sku": "EDGE-ORIN", "cantidad": 40}),
                (
                    "consultar_capacidad_despacho",
                    {"fecha": "2026-03-17", "cantidad": 12},
                ),
                ("resumen_ventas", {"sku": "EDGE-ORIN", "cliente_id": "C-1003"}),
            ]:
                resultado = await sesion.call_tool(nombre, argumentos)
                print(f"\n=== LLAMADA {nombre} ===")
                print(_texto(resultado.content))

            recursos = await sesion.list_resources()
            print("\n=== RECURSOS ===")
            for recurso in recursos.resources:
                print(f"- {recurso.uri}")

            politica = await sesion.read_resource("politica://compromiso-entrega")
            print("\n=== RECURSO politica://compromiso-entrega (extracto) ===")
            print(_texto(politica.contents)[:400])

            prompts = await sesion.list_prompts()
            print("\n=== PROMPTS ===")
            for prompt in prompts.prompts:
                print(f"- {prompt.name}")

            renderizado = await sesion.get_prompt(
                "evaluar_compromiso",
                arguments={
                    "cliente_id": "C-1004",
                    "sku": "EDGE-ORIN",
                    "cantidad": "12",
                    "fecha": "2026-03-17",
                },
            )
            print("\n=== PROMPT evaluar_compromiso ===")
            for mensaje in renderizado.messages:
                print(_texto(mensaje.content))


if __name__ == "__main__":
    asyncio.run(principal())

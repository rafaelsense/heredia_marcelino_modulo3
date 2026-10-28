"""CLI del workflow de compromisos de entrega del caso LOG-001."""

import argparse
import asyncio
import json
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from . import rag
from .config_caso import resumen_escenario
from .estado_workflow import SolicitudLogistica
from .workflow import ejecutar_workflow, extractor_llm, reanudar_workflow

RUTA_RAIZ = Path(__file__).resolve().parents[2]
CACHE_LEXICO = RUTA_RAIZ / ".cache" / "politicas_index_lexico.json"
RUTA_CHECKPOINTS = RUTA_RAIZ / "data" / "checkpoints.db"


def _parser() -> argparse.ArgumentParser:
    """Define los argumentos del CLI: ejecución nueva o reanudación HITL."""
    parser = argparse.ArgumentParser(
        prog="agente_logistico",
        description="Ejecuta el workflow de compromiso de entrega LOG-001",
    )
    parser.add_argument("--solicitud", help="Solicitud en lenguaje natural (requiere API)")
    parser.add_argument("--cliente", help="Identificador del cliente, p. ej. C-1003")
    parser.add_argument("--sku", help="SKU del producto, p. ej. EDGE-ORIN")
    parser.add_argument("--cantidad", type=int, help="Unidades solicitadas (> 0)")
    parser.add_argument("--fecha", help="Fecha de entrega ISO YYYY-MM-DD")
    parser.add_argument("--almacen", default="ALM-LIM", help="Almacén de despacho")
    parser.add_argument(
        "--id-hilo",
        required=True,
        help="Identificador del hilo: persiste el checkpoint y permite reanudar",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Usa el embedder léxico local para RAG sin llamadas externas",
    )
    parser.add_argument(
        "--reanudar",
        action="store_true",
        help="Reanuda un hilo pausado en aprobación con --decision y --supervisor",
    )
    parser.add_argument(
        "--decision", choices=["aprobado", "rechazado"], help="Decisión del supervisor"
    )
    parser.add_argument("--supervisor", help="Nombre del supervisor que decide")
    parser.add_argument("--comentario", default="", help="Comentario del supervisor")
    return parser


async def _ejecutar(argumentos: argparse.Namespace) -> dict:
    """Resuelve el modo de entrada y ejecuta o reanuda el workflow."""
    embedder = rag.embedder_lexico if argumentos.offline else None
    rag_cache = CACHE_LEXICO if argumentos.offline else None

    async with AsyncSqliteSaver.from_conn_string(str(RUTA_CHECKPOINTS)) as checkpointer:
        if argumentos.reanudar:
            if not argumentos.decision or not argumentos.supervisor:
                raise SystemExit("Para reanudar indica --decision y --supervisor.")
            return await reanudar_workflow(
                argumentos.id_hilo,
                decision=argumentos.decision,
                supervisor=argumentos.supervisor,
                comentario=argumentos.comentario,
                embedder=embedder,
                rag_cache=rag_cache,
                checkpointer=checkpointer,
            )

        estructurada = all(
            [argumentos.cliente, argumentos.sku, argumentos.cantidad, argumentos.fecha]
        )
        if not estructurada and not argumentos.solicitud:
            raise SystemExit(
                "Indica --solicitud en lenguaje natural o los cuatro campos "
                "estructurados: --cliente --sku --cantidad --fecha."
            )
        solicitud = None
        extractor = None
        if estructurada:
            solicitud = SolicitudLogistica(
                cliente_id=argumentos.cliente,
                sku=argumentos.sku,
                cantidad=argumentos.cantidad,
                fecha_entrega=argumentos.fecha,
                almacen=argumentos.almacen,
            )
        else:
            extractor = extractor_llm()

        original = argumentos.solicitud or (
            f"{argumentos.cantidad} x {argumentos.sku} para {argumentos.cliente} "
            f"el {argumentos.fecha} desde {argumentos.almacen}"
        )
        return await ejecutar_workflow(
            original,
            solicitud=solicitud,
            id_solicitud=argumentos.id_hilo,
            extractor=extractor,
            embedder=embedder,
            rag_cache=rag_cache,
            checkpointer=checkpointer,
        )


def main() -> None:
    """Imprime el escenario, ejecuta el workflow y muestra el estado final."""
    from dotenv import load_dotenv

    load_dotenv()
    argumentos = _parser().parse_args()
    print(json.dumps({"escenario": resumen_escenario()}, ensure_ascii=False, indent=2))
    estado = asyncio.run(_ejecutar(argumentos))

    interrupciones = estado.get("__interrupt__", [])
    if interrupciones:
        pausa = interrupciones[0].value
        estado["hitl_pendiente"] = pausa
        estado["mensaje"] = (
            f"{pausa['motivo']} Costo extraordinario: "
            f"USD {pausa['costo_extraordinario_usd']}. Reanuda con: "
            f"python -m agente_logistico --reanudar --id-hilo {argumentos.id_hilo} "
            "--decision aprobado|rechazado --supervisor \"Nombre\""
        )
        estado["estado"] = "pendiente_aprobacion"
        estado.pop("__interrupt__", None)
    print(json.dumps(estado, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

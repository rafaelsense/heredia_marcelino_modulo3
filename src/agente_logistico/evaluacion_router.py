"""Evaluación reproducible de los casos del router logístico."""

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from .contratos import RouteDecision
from .router import DeterministicRouter, HybridRouter, ModelRouter

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_CASOS = RUTA_RAIZ / "data" / "router_cases.json"


def cargar_casos(ruta: Path = RUTA_CASOS) -> list[dict]:
    """Carga los casos esperados desde un archivo versionado."""
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


async def evaluar(strategy: str, casos: list[dict], delay: float = 0.0) -> dict:
    """Compara la ruta obtenida con la esperada y resume la exactitud.

    `delay` agrega una pausa entre casos para respetar límites de cuota por
    minuto de proveedores con nivel gratuito.
    """
    if strategy == "deterministic":
        router = DeterministicRouter()
    elif strategy == "model":
        router = ModelRouter()
    elif strategy == "hybrid":
        router = HybridRouter()
    else:
        raise ValueError(f"Estrategia no soportada: {strategy}")

    resultados: list[dict] = []
    aciertos = 0
    for indice, caso in enumerate(casos):
        if indice and delay:
            await asyncio.sleep(delay)
        if strategy == "deterministic":
            decision: RouteDecision = router.route(caso["q"])
        else:
            decision = await router.route(caso["q"])
        correcto = decision.route.value == caso["expected"]
        aciertos += int(correcto)
        resultados.append(
            {
                "query": caso["q"],
                "expected": caso["expected"],
                "actual": decision.route.value,
                "correct": correcto,
                "confidence": decision.confidence,
                "reason": decision.reason,
            }
        )
    return {
        "strategy": strategy,
        "total": len(casos),
        "correct": aciertos,
        "accuracy": round(aciertos / len(casos), 4) if casos else 0.0,
        "results": resultados,
    }


async def main() -> int:
    """Ejecuta la evaluación y devuelve error si algún caso falla."""
    parser = argparse.ArgumentParser(description="Evalúa el router de LOG-001")
    parser.add_argument("--strategy", choices=["deterministic", "model", "hybrid"], default="deterministic")
    parser.add_argument("--cases", type=Path, default=RUTA_CASOS)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Pausa en segundos entre casos (cuotas por minuto del proveedor)",
    )
    argumentos = parser.parse_args()
    load_dotenv()
    resultado = await evaluar(
        argumentos.strategy, cargar_casos(argumentos.cases), argumentos.delay
    )
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0 if resultado["correct"] == resultado["total"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

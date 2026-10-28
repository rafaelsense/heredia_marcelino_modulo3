"""Calibración medible del umbral de abstención RAG.

Mide el mejor score de consultas etiquetadas (relevantes e irrelevantes) y
recomienda el umbral como el punto medio del hueco entre ambos grupos, para
maximizar el margen de error en ambos lados. La recomendación depende del
modelo de embeddings activo: cada proveedor tiene su propia distribución de
similitud coseno, por eso el umbral final se configura con `RAG_MIN_SCORE`.
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from . import rag

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_CALIBRACION = RUTA_RAIZ / "data" / "rag_calibracion.json"


def cargar_consultas(ruta: Path = RUTA_CALIBRACION) -> list[dict]:
    """Carga las consultas etiquetadas desde un archivo versionado."""
    consultas = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not any(c["relevante"] for c in consultas) or not any(
        not c["relevante"] for c in consultas
    ):
        raise ValueError("Se necesitan consultas relevantes e irrelevantes")
    return consultas


def medir_scores(
    consultas: list[dict],
    *,
    embedder=None,
    docs_dir: Path = rag.DOCS_DIR,
    cache_path: Path = rag.CACHE_PATH,
) -> list[dict]:
    """Ejecuta cada consulta y registra el mejor score obtenido."""
    mediciones = []
    for consulta in consultas:
        resultados = rag.search(
            consulta["q"],
            top_k=1,
            embedder=embedder,
            docs_dir=docs_dir,
            cache_path=cache_path,
            min_score=0.0,
        )
        mediciones.append(
            {
                "q": consulta["q"],
                "relevante": consulta["relevante"],
                "mejor_score": resultados[0]["score"] if resultados else 0.0,
                "source_ref": resultados[0]["source_ref"] if resultados else None,
            }
        )
    return mediciones


def recomendar_umbral(mediciones: list[dict]) -> dict:
    """Recomienda el punto medio del hueco entre irrelevantes y relevantes.

    Si los grupos se solapan, no existe umbral que separe ambos y se informa
    el solapamiento en lugar de recomendar un valor engañoso.
    """
    relevantes = [m["mejor_score"] for m in mediciones if m["relevante"]]
    irrelevantes = [m["mejor_score"] for m in mediciones if not m["relevante"]]
    min_relevante = min(relevantes)
    max_irrelevante = max(irrelevantes)
    informe = {
        "min_relevante": round(min_relevante, 4),
        "max_irrelevante": round(max_irrelevante, 4),
        "separable": min_relevante > max_irrelevante,
        "umbral_actual": float(os.getenv("RAG_MIN_SCORE", "0.25")),
        "mediciones": mediciones,
    }
    if min_relevante > max_irrelevante:
        punto_medio = (max_irrelevante + min_relevante) / 2
        informe["umbral_recomendado"] = round(punto_medio, 2)
        informe["margen"] = round((min_relevante - max_irrelevante) / 2, 4)
    else:
        informe["umbral_recomendado"] = None
        informe["advertencia"] = (
            "Los grupos se solapan: ningún umbral separa ambos; "
            "revisa el corpus o el modelo de embeddings."
        )
    return informe


def main() -> int:
    """Ejecuta la calibración y devuelve error si los grupos no se separan."""
    parser = argparse.ArgumentParser(description="Calibra el umbral de abstención RAG")
    parser.add_argument("--consultas", type=Path, default=RUTA_CALIBRACION)
    argumentos = parser.parse_args()
    load_dotenv()

    consultas = cargar_consultas(argumentos.consultas)
    informe = recomendar_umbral(medir_scores(consultas))
    informe["modelo_embeddings"] = os.getenv("EMBEDDING_MODEL") or "por defecto del proveedor"
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    return 0 if informe["separable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Recuperación semántica local con caché invalidada por contenido y modelo."""

import hashlib
import json
import math
import os
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from .modelo import modelo_embeddings, resolver_proveedor

RUTA_RAIZ = Path(__file__).resolve().parents[2]
DOCS_DIR = RUTA_RAIZ / "docs"
CACHE_PATH = RUTA_RAIZ / ".cache" / "politicas_index.json"


@dataclass(frozen=True)
class Chunk:
    """Fragmento documental con procedencia para citar la evidencia."""

    source: str
    section: str
    text: str


def cargar_chunks(docs_dir: Path = DOCS_DIR) -> list[Chunk]:
    """Divide las políticas Markdown por secciones de segundo nivel."""
    chunks: list[Chunk] = []
    for ruta in sorted(Path(docs_dir).glob("politica_*.md")):
        contenido = ruta.read_text(encoding="utf-8")
        partes = [parte.strip() for parte in contenido.split("\n## ") if parte.strip()]
        for indice, parte in enumerate(partes):
            texto = parte if indice == 0 else "## " + parte
            seccion = texto.splitlines()[0].lstrip("# ").strip()
            chunks.append(Chunk(ruta.name, seccion, texto))
    if not chunks:
        raise FileNotFoundError("No se encontraron políticas Markdown para indexar")
    return chunks


def _fingerprint(chunks: list[Chunk]) -> str:
    """Calcula una huella para invalidar la caché cuando cambia el corpus."""
    contenido = "\n".join(f"{c.source}|{c.section}|{c.text}" for c in chunks)
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    """Calcula similitud coseno y valida dimensiones compatibles."""
    if len(a) != len(b):
        raise ValueError("Los embeddings tienen dimensiones incompatibles")
    norma_a = math.sqrt(sum(valor * valor for valor in a))
    norma_b = math.sqrt(sum(valor * valor for valor in b))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (norma_a * norma_b)


def _cliente_embeddings() -> OpenAI:
    """Crea el cliente de embeddings según el proveedor configurado."""
    _, base_url, api_key = resolver_proveedor()
    return OpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))


def _embed(textos: list[str], modelo: str) -> list[list[float]]:
    """Solicita embeddings al proveedor configurado en el entorno."""
    respuesta = _cliente_embeddings().embeddings.create(model=modelo, input=textos)
    return [item.embedding for item in respuesta.data]


def embedder_lexico(textos: list[str], modelo: str, dimensiones: int = 512) -> list[list[float]]:
    """Genera vectores deterministas por hashing de tokens, sin llamadas externas.

    Solo para ejecución offline de demostración; la recuperación de producción
    usa embeddings del proveedor configurado.
    """
    vectores: list[list[float]] = []
    for texto in textos:
        normalizado = unicodedata.normalize("NFKD", texto.lower())
        normalizado = "".join(c for c in normalizado if not unicodedata.combining(c))
        vector = [0.0] * dimensiones
        for token in re.findall(r"[a-z0-9]+", normalizado):
            cubeta = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % dimensiones
            vector[cubeta] += 1.0
        vectores.append(vector)
    return vectores


def _load_or_build(
    *,
    embedder: Callable[[list[str], str], list[list[float]]] | None = None,
    docs_dir: Path = DOCS_DIR,
    cache_path: Path = CACHE_PATH,
) -> tuple[list[Chunk], list[list[float]]]:
    """Reutiliza la caché o reconstruye el índice si cambia contenido o modelo."""
    chunks = cargar_chunks(docs_dir)
    fingerprint = _fingerprint(chunks)
    modelo = modelo_embeddings()

    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        if cache.get("fingerprint") == fingerprint and cache.get("model") == modelo:
            return chunks, cache["vectors"]

    generador = embedder or _embed
    vectores = generador([chunk.text for chunk in chunks], modelo)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"fingerprint": fingerprint, "model": modelo, "vectors": vectores}),
        encoding="utf-8",
    )
    return chunks, vectores


def search(
    query: str,
    top_k: int = 3,
    *,
    embedder: Callable[[list[str], str], list[list[float]]] | None = None,
    docs_dir: Path = DOCS_DIR,
    cache_path: Path = CACHE_PATH,
    min_score: float | None = None,
) -> list[dict]:
    """Busca evidencia relevante y devuelve fuentes citables o una lista vacía.

    El umbral se calibra por proveedor con `RAG_MIN_SCORE`: los embeddings de
    Gemini concentran la similitud coseno en valores altos incluso para texto
    irrelevante, así que requieren un umbral mayor que el embedder léxico.
    """
    if not query.strip():
        raise ValueError("La consulta documental no puede estar vacía")
    if min_score is None:
        min_score = float(os.getenv("RAG_MIN_SCORE", "0.25"))
    chunks, vectores = _load_or_build(
        embedder=embedder,
        docs_dir=docs_dir,
        cache_path=cache_path,
    )
    modelo = modelo_embeddings()
    vector_query = (embedder or _embed)([query], modelo)[0]

    candidatos = [
        (_cosine(vector_query, vector), indice)
        for indice, vector in enumerate(vectores)
    ]
    candidatos.sort(key=lambda item: item[0], reverse=True)
    limite = max(1, min(top_k, 5))

    resultados: list[dict] = []
    for score, indice in candidatos[:limite]:
        if score < min_score:
            continue
        chunk = chunks[indice]
        resultados.append(
            {
                "source": chunk.source,
                "section": chunk.section,
                "score": round(score, 4),
                "content": chunk.text,
                "source_ref": f"[RAG:{chunk.source}#{chunk.section}]",
            }
        )
    return resultados

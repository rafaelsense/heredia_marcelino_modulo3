import unicodedata

from agente_logistico import rag
from agente_logistico.contratos import Route
from agente_logistico.router import DeterministicRouter

VOCABULARIO = ("ventana", "entrega", "extraordinario", "aprobacion", "supervisor")


def embedder_prueba(textos: list[str], modelo: str) -> list[list[float]]:
    """Genera vectores deterministas por palabras para evitar llamadas externas."""
    vectores = []
    for texto in textos:
        normalizado = unicodedata.normalize("NFKD", texto.lower())
        normalizado = "".join(c for c in normalizado if not unicodedata.combining(c))
        vectores.append([float(normalizado.count(palabra)) for palabra in VOCABULARIO])
    return vectores


def crear_docs(tmp_path):
    """Crea un corpus mínimo equivalente a las dos políticas del proyecto."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "politica_compromiso_entrega.md").write_text(
        "# Compromiso\n\n## Ventana\nLa ventana de entrega estándar usa días hábiles.\n",
        encoding="utf-8",
    )
    (docs / "politica_despacho_extraordinario.md").write_text(
        "# Extraordinario\n\n## Aprobación\nEl supervisor aprueba el despacho extraordinario.\n",
        encoding="utf-8",
    )
    return docs


def test_rag_recupera_la_politica_de_compromiso(tmp_path):
    docs = crear_docs(tmp_path)
    resultados = rag.search(
        "¿Cuál es la ventana de entrega?",
        embedder=embedder_prueba,
        docs_dir=docs,
        cache_path=tmp_path / "cache.json",
    )

    assert resultados
    assert resultados[0]["source"] == "politica_compromiso_entrega.md"
    assert resultados[0]["source_ref"].startswith("[RAG:")


def test_rag_recupera_la_politica_extraordinaria(tmp_path):
    docs = crear_docs(tmp_path)
    resultados = rag.search(
        "¿Qué supervisor aprueba el despacho extraordinario?",
        embedder=embedder_prueba,
        docs_dir=docs,
        cache_path=tmp_path / "cache.json",
    )

    assert resultados
    assert resultados[0]["source"] == "politica_despacho_extraordinario.md"
    assert "Aprobación" in resultados[0]["section"]


def test_rag_se_abstiene_cuando_la_evidencia_es_irrelevante(tmp_path):
    docs = crear_docs(tmp_path)
    resultados = rag.search(
        "órbitas planetarias y astronomía",
        embedder=embedder_prueba,
        docs_dir=docs,
        cache_path=tmp_path / "cache.json",
    )

    assert resultados == []


def test_una_consulta_de_stock_no_debe_usar_rag():
    decision = DeterministicRouter().route("¿Qué stock hay de EDGE-ORIN?")

    assert decision.route == Route.TOOLS

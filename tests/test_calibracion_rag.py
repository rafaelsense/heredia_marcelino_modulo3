import json
import unicodedata

from agente_logistico.calibracion_rag import (
    cargar_consultas,
    medir_scores,
    recomendar_umbral,
)
from agente_logistico.rag import embedder_lexico

from test_rag import crear_docs


def test_cargar_consultas_exige_ambos_grupos(tmp_path):
    ruta = tmp_path / "consultas.json"
    ruta.write_text(json.dumps([{"q": "solo relevante", "relevante": True}]))

    try:
        cargar_consultas(ruta)
        assert False, "Debería rechazar un conjunto sin irrelevantes"
    except ValueError as exc:
        assert "relevantes e irrelevantes" in str(exc)


def test_umbral_recomendado_es_el_punto_medio_del_hueco(tmp_path):
    docs = crear_docs(tmp_path)
    consultas = [
        {"q": "¿Cuál es la ventana de entrega?", "relevante": True},
        {"q": "¿Qué supervisor aprueba el despacho extraordinario?", "relevante": True},
        {"q": "órbitas planetarias y astronomía", "relevante": False},
        {"q": "recetas de cocina italiana", "relevante": False},
    ]
    mediciones = medir_scores(
        consultas,
        embedder=embedder_lexico,
        docs_dir=docs,
        cache_path=tmp_path / "cache.json",
    )
    informe = recomendar_umbral(mediciones)

    assert informe["separable"]
    esperado = (informe["max_irrelevante"] + informe["min_relevante"]) / 2
    assert informe["umbral_recomendado"] == round(esperado, 2)
    assert informe["margen"] > 0


def test_grupos_solapados_no_recomiendan_umbral():
    mediciones = [
        {"q": "a", "relevante": True, "mejor_score": 0.5},
        {"q": "b", "relevante": False, "mejor_score": 0.7},
    ]
    informe = recomendar_umbral(mediciones)

    assert not informe["separable"]
    assert informe["umbral_recomendado"] is None
    assert "solapan" in informe["advertencia"]

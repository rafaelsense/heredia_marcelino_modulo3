import asyncio
import unicodedata

import pytest

from agente_logistico import rag
from agente_logistico.estado_workflow import (
    EstadoLogistico,
    EstadoProceso,
    SolicitudLogistica,
)
from agente_logistico.workflow import build_workflow, ejecutar_workflow

VOCABULARIO = ("ventana", "entrega", "extraordinario", "aprobacion", "supervisor")


def embedder_prueba(textos: list[str], modelo: str) -> list[list[float]]:
    """Genera vectores deterministas por palabras para evitar llamadas externas."""
    vectores = []
    for texto in textos:
        normalizado = unicodedata.normalize("NFKD", texto.lower())
        normalizado = "".join(c for c in normalizado if not unicodedata.combining(c))
        vectores.append([float(normalizado.count(palabra)) for palabra in VOCABULARIO])
    return vectores


def ejecutar(texto: str, tmp_path, **kwargs) -> EstadoLogistico:
    """Ejecuta el workflow de forma síncrona con caché RAG aislada."""
    kwargs.setdefault("embedder", embedder_prueba)
    kwargs.setdefault("rag_cache", tmp_path / "rag_cache.json")
    return asyncio.run(ejecutar_workflow(texto, **kwargs))


def solicitud_dict(**cambios) -> dict:
    """Crea una solicitud estructurada válida con cambios puntuales."""
    base = {
        "cliente_id": "C-1003",
        "sku": "EDGE-ORIN",
        "cantidad": 6,
        "fecha_entrega": "2026-03-19",
    }
    base.update(cambios)
    return base


def test_ruta_directa_confirma_compromiso(bd_temporal, tmp_path):
    estado = ejecutar(
        "6 EDGE-ORIN para C-1003 el 2026-03-19",
        tmp_path,
        solicitud=solicitud_dict(),
        id_solicitud="SOL-TEST-01",
    )

    assert estado["estado"] == EstadoProceso.CONFIRMADO.value
    assert estado["evaluacion"]["decision"] == "directo"
    assert estado["stock_disponible"] == 30
    assert estado["aprobacion"] is None
    assert "[SQL:clientes]" in estado["fuentes"]
    assert "[SQL:inventario]" in estado["fuentes"]
    assert "[SQL:reservas_capacidad]" in estado["fuentes"]
    assert any(fuente.startswith("[RAG:") for fuente in estado["fuentes"])


def test_excepcion_queda_pendiente_de_aprobacion(bd_temporal, tmp_path):
    estado = ejecutar(
        "12 EDGE-ORIN urgentes",
        tmp_path,
        solicitud=solicitud_dict(cliente_id="C-1004", cantidad=12, fecha_entrega="2026-03-17"),
    )

    assert estado["estado"] == EstadoProceso.PENDIENTE_APROBACION.value
    assert estado["evaluacion"]["decision"] == "requiere_aprobacion"
    assert estado["evaluacion"]["tipo_despacho"] == "extraordinario"
    assert estado["evaluacion"]["costo_extraordinario_usd"] == 400
    assert estado["aprobacion"] == {
        "requerida": True,
        "rol": "supervisor_logistica",
        "decision": None,
    }


def test_rechazo_por_stock_insuficiente(bd_temporal, tmp_path):
    estado = ejecutar(
        "40 EDGE-ORIN",
        tmp_path,
        solicitud=solicitud_dict(cantidad=40),
    )

    assert estado["estado"] == EstadoProceso.RECHAZADO.value
    assert "Stock insuficiente" in estado["mensaje"]
    assert estado["evaluacion"]["tipo_despacho"] == "no_viable"


def test_rechazo_por_cliente_bloqueado(bd_temporal, tmp_path):
    estado = ejecutar(
        "2 CAM-IP67 para C-1005",
        tmp_path,
        solicitud=solicitud_dict(cliente_id="C-1005", sku="CAM-IP67", cantidad=2),
    )

    assert estado["estado"] == EstadoProceso.RECHAZADO.value
    assert "bloqueado" in estado["mensaje"]
    assert estado["evaluacion"] is None


def test_sku_inexistente_cierra_con_rechazo(bd_temporal, tmp_path):
    estado = ejecutar(
        "5 SKU-FALSO",
        tmp_path,
        solicitud=solicitud_dict(sku="SKU-FALSO", cantidad=5),
    )

    assert estado["estado"] == EstadoProceso.RECHAZADO.value
    assert "SKU" in estado["mensaje"]


def test_extraccion_invalida_deriva_a_aclaracion(bd_temporal, tmp_path):
    def extractor_fallo(texto: str) -> SolicitudLogistica:
        raise ValueError("faltan campos obligatorios")

    estado = ejecutar("hola, ¿qué tal?", tmp_path, extractor=extractor_fallo)

    assert estado["estado"] == EstadoProceso.ACLARACION.value
    assert estado["solicitud"] is None
    assert estado["fuentes"] == []
    assert "cliente" in estado["mensaje"]


def test_entrada_estructurada_invalida_deriva_a_aclaracion(bd_temporal, tmp_path):
    estado = ejecutar("cantidad cero", tmp_path, solicitud=solicitud_dict(cantidad=0))

    assert estado["estado"] == EstadoProceso.ACLARACION.value


def test_sin_extractor_ni_estructura_pide_aclaracion(bd_temporal, tmp_path):
    estado = ejecutar("texto libre sin extractor", tmp_path)

    assert estado["estado"] == EstadoProceso.ACLARACION.value
    assert "extractor" in estado["mensaje"]


def test_las_ramas_condicionales_cubren_las_tres_decisiones(bd_temporal, tmp_path):
    solicitudes = [
        (solicitud_dict(), EstadoProceso.CONFIRMADO.value),
        (solicitud_dict(cantidad=12, fecha_entrega="2026-03-17"), EstadoProceso.PENDIENTE_APROBACION.value),
        (solicitud_dict(cantidad=40), EstadoProceso.RECHAZADO.value),
    ]
    resultados = [
        ejecutar("caso", tmp_path, solicitud=solicitud)["estado"]
        for solicitud, _ in solicitudes
    ]

    assert resultados == [esperado for _, esperado in solicitudes]


def test_el_estado_no_guarda_datos_innecesarios(bd_temporal, tmp_path):
    estado = ejecutar("6 EDGE-ORIN", tmp_path, solicitud=solicitud_dict())

    assert set(estado.keys()) <= set(EstadoLogistico.__annotations__.keys())
    contenido = str(estado).lower()
    assert "api_key" not in contenido
    assert "sk-" not in contenido


def test_el_grafo_expone_los_nueve_nodos(bd_temporal):
    grafo = build_workflow()

    assert len(grafo.get_graph().nodes) >= 9


def test_solicitud_logistica_valida_campos():
    with pytest.raises(ValueError):
        SolicitudLogistica(
            cliente_id="C-1003", sku="EDGE-ORIN", cantidad=0, fecha_entrega="2026-03-19"
        )
    with pytest.raises(ValueError):
        SolicitudLogistica(
            cliente_id="C-1003", sku="EDGE-ORIN", cantidad=5, fecha_entrega="19-03-2026"
        )

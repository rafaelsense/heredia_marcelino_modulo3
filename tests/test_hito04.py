"""Pruebas del Hito 04: retry con backoff, checkpoint SQLite y HITL."""

import asyncio

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agente_logistico.estado_workflow import EstadoProceso
from agente_logistico.reintento import (
    ErrorTransitorioSimulado,
    acon_reintento,
    con_reintento,
    simular_fallo_transitorio,
)
from agente_logistico.workflow import ejecutar_workflow, reanudar_workflow

from test_workflow import embedder_prueba, solicitud_dict

ESPERA = {"espera_inicial": 0.01, "factor": 1.0, "jitter": 0.0}


def test_retry_exito_tras_fallo_transitorio():
    intentos = {"n": 0}

    def operacion():
        intentos["n"] += 1
        if intentos["n"] < 2:
            raise ErrorTransitorioSimulado("fallo puntual")
        return "ok"

    assert con_reintento(operacion, intentos=3, **ESPERA) == "ok"
    assert intentos["n"] == 2


def test_retry_agota_intentos_y_propaga():
    def operacion():
        raise ErrorTransitorioSimulado("siempre falla")

    with pytest.raises(ErrorTransitorioSimulado):
        con_reintento(operacion, intentos=3, **ESPERA)


def test_retry_no_reintenta_errores_de_negocio():
    intentos = {"n": 0}

    def operacion():
        intentos["n"] += 1
        raise ValueError("error de negocio, no transitorio")

    with pytest.raises(ValueError):
        con_reintento(operacion, intentos=3, **ESPERA)
    assert intentos["n"] == 1


def test_retry_async():
    intentos = {"n": 0}

    async def operacion():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise ErrorTransitorioSimulado("fallo async")
        return "ok"

    assert asyncio.run(acon_reintento(operacion, intentos=3, **ESPERA)) == "ok"
    assert intentos["n"] == 3


def test_simulacion_falla_una_sola_vez_por_clave(monkeypatch):
    monkeypatch.setenv("SIMULAR_FALLO_TRANSITORIO_CAPACIDAD", "1")

    with pytest.raises(ErrorTransitorioSimulado):
        simular_fallo_transitorio("SOL-X")
    simular_fallo_transitorio("SOL-X")  # la segunda vez pasa

    monkeypatch.setenv("SIMULAR_FALLO_TRANSITORIO_CAPACIDAD", "0")
    simular_fallo_transitorio("SOL-Y")  # desactivada, nunca falla


async def _hasta_pausa(tmp_path, ruta_bd=None):
    """Ejecuta una excepción con checkpoint y devuelve estado y saver."""
    saver_cm = AsyncSqliteSaver.from_conn_string(str(tmp_path / "checkpoints.db"))
    saver = await saver_cm.__aenter__()
    estado = await ejecutar_workflow(
        "12 EDGE-ORIN urgentes",
        solicitud=solicitud_dict(
            cliente_id="C-1004", cantidad=12, fecha_entrega="2026-03-17"
        ),
        id_solicitud="SOL-HITL",
        embedder=embedder_prueba,
        rag_cache=tmp_path / "rag_cache.json",
        checkpointer=saver,
    )
    return estado, saver, saver_cm


def test_hitl_pausa_persiste_en_checkpoint(bd_temporal, tmp_path):
    estado, saver, _ = asyncio.run(_hasta_pausa(tmp_path))

    assert estado["estado"] == EstadoProceso.PENDIENTE_APROBACION.value
    assert "__interrupt__" in estado
    pausa = estado["__interrupt__"][0].value
    assert pausa["tipo"] == "aprobacion_supervisor"
    assert pausa["costo_extraordinario_usd"] == 400


def test_hitl_reanudar_aprobado_confirma_extraordinario(bd_temporal, tmp_path):
    async def flujo():
        _, saver, _ = await _hasta_pausa(tmp_path)
        return await reanudar_workflow(
            "SOL-HITL",
            decision="aprobado",
            supervisor="María Torres",
            comentario="Cliente prioritario",
            embedder=embedder_prueba,
            rag_cache=tmp_path / "rag_cache.json",
            checkpointer=saver,
        )

    estado = asyncio.run(flujo())

    assert estado["estado"] == EstadoProceso.CONFIRMADO.value
    assert estado["aprobacion"]["decision"] == "aprobado"
    assert estado["aprobacion"]["supervisor"] == "María Torres"
    assert "despacho extraordinario" in estado["mensaje"]
    assert "USD 400" in estado["mensaje"]


def test_hitl_reanudar_rechazado_cierra_rechazo(bd_temporal, tmp_path):
    async def flujo():
        _, saver, _ = await _hasta_pausa(tmp_path)
        return await reanudar_workflow(
            "SOL-HITL",
            decision="rechazado",
            supervisor="María Torres",
            comentario="Costo no justificado",
            embedder=embedder_prueba,
            rag_cache=tmp_path / "rag_cache.json",
            checkpointer=saver,
        )

    estado = asyncio.run(flujo())

    assert estado["estado"] == EstadoProceso.RECHAZADO.value
    assert "María Torres" in estado["mensaje"]
    assert "no aprobó" in estado["mensaje"]


def test_reanudar_exige_decision_valida(tmp_path):
    async def flujo():
        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / "checkpoints.db")
        ) as saver:
            await reanudar_workflow(
                "SOL-X", decision="quizá", supervisor="Alguien", checkpointer=saver
            )

    with pytest.raises(ValueError):
        asyncio.run(flujo())


def test_workflow_con_simulacion_de_fallo_transitorio(
    bd_temporal, tmp_path, monkeypatch
):
    """La ruta directa sobrevive a un fallo transitorio de capacidad."""
    monkeypatch.setenv("SIMULAR_FALLO_TRANSITORIO_CAPACIDAD", "1")
    estado = asyncio.run(
        ejecutar_workflow(
            "6 EDGE-ORIN",
            solicitud=solicitud_dict(),
            id_solicitud="SOL-RETRY",
            embedder=embedder_prueba,
            rag_cache=tmp_path / "rag_cache.json",
        )
    )

    assert estado["estado"] == EstadoProceso.CONFIRMADO.value
    assert estado["capacidad"]["capacidad_normal_disponible"] == 6

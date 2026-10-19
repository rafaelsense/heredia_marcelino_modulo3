import json
import subprocess
import sys

from agente_logistico.config_caso import (
    CASO_ID,
    PARAMETROS,
    SEMILLA,
    VARIANTE,
    generar_parametros,
)


def test_parametros_asignados_a_log001():
    assert CASO_ID == "LOG-001"
    assert VARIANTE == "Logística"
    assert SEMILLA == 6739
    assert PARAMETROS.capacidad_diaria == 6
    assert PARAMETROS.ventana_entrega_dias == 3
    assert PARAMETROS.costo_extraordinario_usd == 400


def test_generar_parametros_es_reproducible():
    assert generar_parametros(6739) == generar_parametros(6739)


def test_reinicio_del_proceso_produce_el_mismo_escenario():
    comando = [sys.executable, "-m", "agente_logistico.config_caso"]
    primero = subprocess.run(comando, capture_output=True, text=True, check=True)
    segundo = subprocess.run(comando, capture_output=True, text=True, check=True)

    assert primero.stdout == segundo.stdout
    assert json.loads(primero.stdout) == json.loads(segundo.stdout)

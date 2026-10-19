from datetime import date

import pytest

from agente_logistico.reglas import (
    DecisionCompromiso,
    TipoDespacho,
    evaluar_compromiso,
    sumar_dias_habiles,
)


def evaluar(**cambios):
    parametros = {
        "fecha_solicitud": date(2026, 3, 16),
        "fecha_entrega": date(2026, 3, 19),
        "cantidad": 6,
        "stock_disponible": 30,
        "capacidad_diaria": 6,
        "capacidad_reservada": 0,
        "ventana_entrega_dias": 3,
        "costo_extraordinario_usd": 400,
    }
    parametros.update(cambios)
    return evaluar_compromiso(**parametros)


def test_ruta_directa_con_stock_fecha_y_capacidad_compatibles():
    resultado = evaluar()

    assert resultado.decision == DecisionCompromiso.DIRECTO
    assert resultado.tipo_despacho == TipoDespacho.NORMAL
    assert resultado.costo_extraordinario_usd == 0
    assert resultado.fecha_minima_normal == date(2026, 3, 19)


def test_doce_unidades_para_manana_requieren_aprobacion():
    resultado = evaluar(fecha_entrega=date(2026, 3, 17), cantidad=12)

    assert resultado.decision == DecisionCompromiso.REQUIERE_APROBACION
    assert resultado.tipo_despacho == TipoDespacho.EXTRAORDINARIO
    assert resultado.costo_extraordinario_usd == 400
    assert resultado.capacidad_normal_disponible == 6
    assert resultado.capacidad_extraordinaria_disponible == 12


def test_stock_insuficiente_se_rechaza():
    resultado = evaluar(cantidad=40)

    assert resultado.decision == DecisionCompromiso.RECHAZADO
    assert resultado.tipo_despacho == TipoDespacho.NO_VIABLE
    assert "Stock insuficiente" in resultado.motivo


def test_capacidad_extraordinaria_insuficiente_se_rechaza():
    resultado = evaluar(fecha_entrega=date(2026, 3, 17), cantidad=13)

    assert resultado.decision == DecisionCompromiso.RECHAZADO
    assert "Capacidad insuficiente" in resultado.motivo


def test_entrega_el_mismo_dia_se_rechaza():
    resultado = evaluar(fecha_entrega=date(2026, 3, 16))

    assert resultado.decision == DecisionCompromiso.RECHAZADO
    assert "siguiente día hábil" in resultado.motivo


def test_reserva_de_capacidad_puede_convertir_la_entrega_en_excepcion():
    resultado = evaluar(capacidad_reservada=1)

    assert resultado.decision == DecisionCompromiso.REQUIERE_APROBACION
    assert resultado.capacidad_normal_disponible == 5


@pytest.mark.parametrize(
    "cambio",
    [
        {"cantidad": 0},
        {"stock_disponible": -1},
        {"capacidad_diaria": 0},
        {"capacidad_reservada": -1},
        {"ventana_entrega_dias": 0},
        {"costo_extraordinario_usd": -1},
    ],
)
def test_parametros_invalidos_se_rechazan_en_la_frontera(cambio):
    with pytest.raises(ValueError):
        evaluar(**cambio)


def test_suma_de_dias_habiles_omite_fin_de_semana():
    assert sumar_dias_habiles(date(2026, 3, 13), 1) == date(2026, 3, 16)

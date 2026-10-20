from agente_logistico import servicios


def test_consultar_cliente_existente(bd_temporal):
    resultado = servicios.consultar_cliente(" c-1003 ")

    assert resultado["ok"] is True
    assert resultado["cliente"]["estado"] == "activo"
    assert resultado["source_ref"] == "[SQL:clientes]"


def test_consultar_cliente_inexistente(bd_temporal):
    resultado = servicios.consultar_cliente("C-9999")

    assert resultado["ok"] is False
    assert resultado["error_type"] == "cliente_no_encontrado"


def test_disponibilidad_suficiente_e_insuficiente(bd_temporal):
    suficiente = servicios.consultar_disponibilidad("EDGE-ORIN", 6)
    insuficiente = servicios.consultar_disponibilidad("EDGE-ORIN", 40)

    assert suficiente["suficiente"] is True
    assert insuficiente["ok"] is True
    assert insuficiente["suficiente"] is False
    assert insuficiente["stock_disponible"] == 30


def test_disponibilidad_sku_inexistente_y_cantidad_invalida(bd_temporal):
    inexistente = servicios.consultar_disponibilidad("SKU-INEXISTENTE", 1)
    invalida = servicios.consultar_disponibilidad("EDGE-ORIN", 0)

    assert inexistente["error_type"] == "sku_no_encontrado"
    assert invalida["error_type"] == "cantidad_invalida"


def test_capacidad_descuenta_reservas(bd_temporal):
    resultado = servicios.consultar_capacidad_despacho("2026-03-18", 4)

    assert resultado["ok"] is True
    assert resultado["capacidad_reservada"] == 2
    assert resultado["capacidad_normal_disponible"] == 4
    assert resultado["capacidad_extraordinaria_disponible"] == 10
    assert resultado["suficiente_normal"] is True


def test_capacidad_extraordinaria_para_doce_unidades(bd_temporal):
    resultado = servicios.consultar_capacidad_despacho("2026-03-17", 12)

    assert resultado["suficiente_normal"] is False
    assert resultado["suficiente_extraordinaria"] is True


def test_resumen_ventas_sin_filtros(bd_temporal):
    resultado = servicios.resumen_ventas()

    assert resultado["transacciones"] == 6
    assert resultado["unidades"] == 28
    assert resultado["ingresos_usd"] == 34350.0
    assert resultado["source_ref"] == "[SQL:ventas]"


def test_resumen_ventas_con_sku_y_cliente(bd_temporal):
    resultado = servicios.resumen_ventas(sku="edge-orin", cliente_id="c-1003")

    assert resultado["transacciones"] == 2
    assert resultado["unidades"] == 12
    assert resultado["ingresos_usd"] == 22800.0


def test_resumen_ventas_con_rango_de_fechas(bd_temporal):
    resultado = servicios.resumen_ventas(
        fecha_desde="2026-01-01",
        fecha_hasta="2026-03-31",
    )

    assert resultado["transacciones"] == 6
    assert resultado["unidades"] == 28


def test_sql_no_interpola_un_valor_con_aspecto_malicioso(bd_temporal):
    resultado = servicios.resumen_ventas(sku="EDGE-ORIN' OR 1=1 --")

    assert resultado["transacciones"] == 0
    assert resultado["unidades"] == 0


def test_resumen_ventas_rechaza_fecha_invalida(bd_temporal):
    resultado = servicios.resumen_ventas(fecha_desde="31-03-2026")

    assert resultado["ok"] is False
    assert resultado["error_type"] == "fecha_invalida"

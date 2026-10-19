import sqlite3

from agente_logistico.inicializar_datos import TABLAS_DATOS, inicializar_bd


def capturar_datos(ruta):
    with sqlite3.connect(ruta) as conexion:
        return {
            tabla: conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1").fetchall()
            for tabla in TABLAS_DATOS
        }


def test_inicializa_datos_minimos_y_parametros(tmp_path):
    ruta = inicializar_bd(tmp_path / "logistica.db")

    with sqlite3.connect(ruta) as conexion:
        conteos = {
            tabla: conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            for tabla in TABLAS_DATOS
        }
        parametros = conexion.execute(
            "SELECT caso_id, semilla, capacidad_diaria, "
            "ventana_entrega_dias, costo_extraordinario_usd "
            "FROM parametros_escenario"
        ).fetchone()

    assert conteos == {
        "parametros_escenario": 1,
        "clientes": 3,
        "productos": 2,
        "inventario": 2,
        "ventas": 6,
        "reservas_capacidad": 2,
    }
    assert parametros == ("LOG-001", 6739, 6, 3, 400)


def test_reinicializar_restaura_exactamente_los_datos(tmp_path):
    ruta = inicializar_bd(tmp_path / "logistica.db")
    inicial = capturar_datos(ruta)

    with sqlite3.connect(ruta) as conexion:
        conexion.execute(
            "UPDATE inventario SET stock_disponible = ? WHERE sku = ?",
            (99, "EDGE-ORIN"),
        )
    inicializar_bd(ruta)

    assert capturar_datos(ruta) == inicial

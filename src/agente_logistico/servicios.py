"""Servicios de dominio compartidos por tools, workflow y MCP."""

import sqlite3
from datetime import date
from pathlib import Path

from .config_caso import PARAMETROS
from .inicializar_datos import RUTA_BD


def _error(tipo: str, mensaje: str, recuperable: bool = True) -> dict:
    """Devuelve un error homogéneo para todas las capacidades del agente."""
    return {
        "ok": False,
        "error_type": tipo,
        "message": mensaje,
        "recoverable": recuperable,
    }


def _ruta(ruta_bd: Path | str | None) -> Path:
    """Resuelve la base activa permitiendo rutas temporales en pruebas."""
    return Path(ruta_bd) if ruta_bd is not None else RUTA_BD


def consultar_cliente(cliente_id: str, ruta_bd: Path | str | None = None) -> dict:
    """Obtiene el estado logístico de un cliente sin modificar la base."""
    cliente_normalizado = cliente_id.strip().upper()
    with sqlite3.connect(_ruta(ruta_bd)) as conexion:
        conexion.row_factory = sqlite3.Row
        fila = conexion.execute(
            "SELECT cliente_id, nombre, region, estado FROM clientes WHERE cliente_id = ?",
            (cliente_normalizado,),
        ).fetchone()
    if fila is None:
        return _error("cliente_no_encontrado", f"Cliente no encontrado: {cliente_normalizado}")
    return {"ok": True, "cliente": dict(fila), "source_ref": "[SQL:clientes]"}


def consultar_disponibilidad(
    sku: str,
    cantidad: int,
    ruta_bd: Path | str | None = None,
) -> dict:
    """Compara el stock actual con una cantidad solicitada."""
    if cantidad <= 0:
        return _error("cantidad_invalida", "La cantidad debe ser mayor que cero")
    sku_normalizado = sku.strip().upper()
    with sqlite3.connect(_ruta(ruta_bd)) as conexion:
        conexion.row_factory = sqlite3.Row
        fila = conexion.execute(
            "SELECT sku, almacen, stock_disponible FROM inventario WHERE sku = ?",
            (sku_normalizado,),
        ).fetchone()
    if fila is None:
        return _error("sku_no_encontrado", f"SKU o stock no encontrado: {sku_normalizado}")
    stock = int(fila["stock_disponible"])
    return {
        "ok": True,
        "sku": sku_normalizado,
        "almacen": fila["almacen"],
        "cantidad_solicitada": cantidad,
        "stock_disponible": stock,
        "suficiente": cantidad <= stock,
        "source_ref": "[SQL:inventario]",
    }


def consultar_capacidad_despacho(
    fecha: str,
    cantidad: int,
    almacen: str = "ALM-LIM",
    ruta_bd: Path | str | None = None,
) -> dict:
    """Calcula capacidad normal y extraordinaria disponible para una fecha."""
    if cantidad <= 0:
        return _error("cantidad_invalida", "La cantidad debe ser mayor que cero")
    try:
        fecha_despacho = date.fromisoformat(fecha).isoformat()
    except ValueError:
        return _error("fecha_invalida", "La fecha debe tener formato ISO YYYY-MM-DD")

    almacen_normalizado = almacen.strip().upper()
    with sqlite3.connect(_ruta(ruta_bd)) as conexion:
        reservada = conexion.execute(
            "SELECT COALESCE(SUM(cantidad), 0) FROM reservas_capacidad "
            "WHERE almacen = ? AND fecha_despacho = ?",
            (almacen_normalizado, fecha_despacho),
        ).fetchone()[0]

    normal = max(PARAMETROS.capacidad_diaria - int(reservada), 0)
    extraordinaria = max(PARAMETROS.capacidad_diaria * 2 - int(reservada), 0)
    return {
        "ok": True,
        "almacen": almacen_normalizado,
        "fecha": fecha_despacho,
        "cantidad_solicitada": cantidad,
        "capacidad_diaria": PARAMETROS.capacidad_diaria,
        "capacidad_reservada": int(reservada),
        "capacidad_normal_disponible": normal,
        "capacidad_extraordinaria_disponible": extraordinaria,
        "suficiente_normal": cantidad <= normal,
        "suficiente_extraordinaria": cantidad <= extraordinaria,
        "source_ref": "[SQL:reservas_capacidad]",
    }


def resumen_ventas(
    sku: str | None = None,
    cliente_id: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    ruta_bd: Path | str | None = None,
) -> dict:
    """Resume ventas históricas con filtros fijos y valores parametrizados."""
    filtros: list[str] = []
    parametros: list[str] = []
    if sku:
        filtros.append("sku = ?")
        parametros.append(sku.strip().upper())
    if cliente_id:
        filtros.append("cliente_id = ?")
        parametros.append(cliente_id.strip().upper())
    try:
        if fecha_desde:
            filtros.append("fecha >= ?")
            parametros.append(date.fromisoformat(fecha_desde).isoformat())
        if fecha_hasta:
            filtros.append("fecha <= ?")
            parametros.append(date.fromisoformat(fecha_hasta).isoformat())
    except ValueError:
        return _error("fecha_invalida", "Las fechas deben tener formato ISO YYYY-MM-DD")

    clausula = f" WHERE {' AND '.join(filtros)}" if filtros else ""
    consulta = (
        "SELECT COUNT(*) AS transacciones, "
        "COALESCE(SUM(cantidad), 0) AS unidades, "
        "ROUND(COALESCE(SUM(monto_usd), 0), 2) AS ingresos_usd "
        "FROM ventas" + clausula
    )
    with sqlite3.connect(_ruta(ruta_bd)) as conexion:
        conexion.row_factory = sqlite3.Row
        fila = dict(conexion.execute(consulta, tuple(parametros)).fetchone())
    return {
        "ok": True,
        "filters": {
            "sku": sku.strip().upper() if sku else None,
            "cliente_id": cliente_id.strip().upper() if cliente_id else None,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
        **fila,
        "source_ref": "[SQL:ventas]",
    }

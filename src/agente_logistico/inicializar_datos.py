"""Inicialización reproducible de la base sintética SQLite de LOG-001."""

import argparse
import json
import sqlite3
from pathlib import Path

from .config_caso import (
    CASO_ID,
    FECHA_REFERENCIA,
    PARAMETROS,
    SEMILLA,
    VARIANTE,
)

RUTA_RAIZ = Path(__file__).resolve().parents[2]
RUTA_BD = RUTA_RAIZ / "data" / "logistica.db"
TABLAS_DATOS = (
    "parametros_escenario",
    "clientes",
    "productos",
    "inventario",
    "ventas",
    "reservas_capacidad",
)


def crear_esquema(conexion: sqlite3.Connection) -> None:
    """Crea las tablas y restricciones de integridad del escenario logístico."""
    conexion.executescript(
        """
        CREATE TABLE parametros_escenario (
            caso_id TEXT PRIMARY KEY,
            variante TEXT NOT NULL,
            semilla INTEGER NOT NULL,
            capacidad_diaria INTEGER NOT NULL CHECK (capacidad_diaria > 0),
            ventana_entrega_dias INTEGER NOT NULL CHECK (ventana_entrega_dias > 0),
            costo_extraordinario_usd INTEGER NOT NULL CHECK (costo_extraordinario_usd >= 0),
            fecha_referencia TEXT NOT NULL
        );

        CREATE TABLE clientes (
            cliente_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            region TEXT NOT NULL,
            estado TEXT NOT NULL CHECK (estado IN ('activo', 'bloqueado'))
        );

        CREATE TABLE productos (
            sku TEXT PRIMARY KEY,
            descripcion TEXT NOT NULL
        );

        CREATE TABLE inventario (
            sku TEXT PRIMARY KEY REFERENCES productos(sku),
            almacen TEXT NOT NULL,
            stock_disponible INTEGER NOT NULL CHECK (stock_disponible >= 0)
        );

        CREATE TABLE ventas (
            venta_id TEXT PRIMARY KEY,
            cliente_id TEXT NOT NULL REFERENCES clientes(cliente_id),
            sku TEXT NOT NULL REFERENCES productos(sku),
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            fecha TEXT NOT NULL,
            monto_usd REAL NOT NULL CHECK (monto_usd >= 0)
        );

        CREATE TABLE reservas_capacidad (
            reserva_id TEXT PRIMARY KEY,
            almacen TEXT NOT NULL,
            fecha_despacho TEXT NOT NULL,
            sku TEXT NOT NULL REFERENCES productos(sku),
            cantidad INTEGER NOT NULL CHECK (cantidad > 0)
        );
        """
    )


def poblar_datos(conexion: sqlite3.Connection) -> None:
    """Inserta los datos sintéticos iniciales usando parámetros separados del SQL."""
    conexion.execute(
        "INSERT INTO parametros_escenario VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            CASO_ID,
            VARIANTE,
            SEMILLA,
            PARAMETROS.capacidad_diaria,
            PARAMETROS.ventana_entrega_dias,
            PARAMETROS.costo_extraordinario_usd,
            FECHA_REFERENCIA.isoformat(),
        ),
    )
    conexion.executemany(
        "INSERT INTO clientes VALUES (?, ?, ?, ?)",
        [
            ("C-1003", "Andes Manufactura", "Lima", "activo"),
            ("C-1004", "Talleres Norte", "La Libertad", "activo"),
            ("C-1005", "Minera Sur", "Arequipa", "bloqueado"),
        ],
    )
    conexion.executemany(
        "INSERT INTO productos VALUES (?, ?)",
        [
            ("EDGE-ORIN", "Computadora edge para visión artificial"),
            ("CAM-IP67", "Cámara industrial protección IP67"),
        ],
    )
    conexion.executemany(
        "INSERT INTO inventario VALUES (?, ?, ?)",
        [
            ("EDGE-ORIN", "ALM-LIM", 30),
            ("CAM-IP67", "ALM-LIM", 18),
        ],
    )
    conexion.executemany(
        "INSERT INTO ventas VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("V-001", "C-1003", "EDGE-ORIN", 4, "2026-01-12", 7600.0),
            ("V-002", "C-1004", "CAM-IP67", 6, "2026-01-20", 2700.0),
            ("V-003", "C-1003", "EDGE-ORIN", 8, "2026-02-03", 15200.0),
            ("V-004", "C-1005", "CAM-IP67", 2, "2026-02-11", 900.0),
            ("V-005", "C-1004", "EDGE-ORIN", 3, "2026-02-19", 5700.0),
            ("V-006", "C-1003", "CAM-IP67", 5, "2026-03-02", 2250.0),
        ],
    )
    conexion.executemany(
        "INSERT INTO reservas_capacidad VALUES (?, ?, ?, ?, ?)",
        [
            ("RES-001", "ALM-LIM", "2026-03-18", "EDGE-ORIN", 2),
            ("RES-002", "ALM-LIM", "2026-03-20", "CAM-IP67", 1),
        ],
    )


def inicializar_bd(ruta: Path = RUTA_BD) -> Path:
    """Recrea la base indicada para garantizar siempre el mismo estado inicial."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ruta) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        for tabla in reversed(TABLAS_DATOS):
            conexion.execute(f"DROP TABLE IF EXISTS {tabla}")
        crear_esquema(conexion)
        poblar_datos(conexion)
    return ruta


def resumen_bd(ruta: Path) -> dict:
    """Resume los conteos usados para verificar la inicialización de la base."""
    with sqlite3.connect(ruta) as conexion:
        conteos = {
            tabla: conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            for tabla in TABLAS_DATOS
        }
    return {"base_datos": str(ruta), "registros": conteos}


def main() -> None:
    """Procesa los argumentos y ejecuta la inicialización desde la terminal."""
    parser = argparse.ArgumentParser(description="Inicializa los datos sintéticos de LOG-001")
    parser.add_argument("--bd", type=Path, default=RUTA_BD)
    argumentos = parser.parse_args()
    ruta = inicializar_bd(argumentos.bd)
    print(json.dumps(resumen_bd(ruta), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

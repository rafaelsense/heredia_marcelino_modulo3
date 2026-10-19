"""Configuración reproducible del escenario asignado a LOG-001."""

import json
import random
from dataclasses import asdict, dataclass
from datetime import date

CASO_ID = "LOG-001"
VARIANTE = "Logística"
SEMILLA = 6739
FECHA_REFERENCIA = date(2026, 3, 16)


@dataclass(frozen=True)
class ParametrosCaso:
    """Parámetros del escenario que cambian únicamente mediante la semilla."""

    capacidad_diaria: int
    ventana_entrega_dias: int
    costo_extraordinario_usd: int


def generar_parametros(semilla: int = SEMILLA) -> ParametrosCaso:
    """Genera los parámetros con una secuencia fija y aislada de otra aleatoriedad."""
    rng = random.Random(semilla)
    return ParametrosCaso(
        capacidad_diaria=rng.choice([6, 8, 10, 12]),
        ventana_entrega_dias=rng.choice([2, 3, 4]),
        costo_extraordinario_usd=rng.choice([250, 400, 550]),
    )


PARAMETROS = generar_parametros()


def resumen_escenario() -> dict:
    """Devuelve la identidad y los parámetros que deben mostrarse al iniciar."""
    return {
        "caso_id": CASO_ID,
        "variante": VARIANTE,
        "semilla": SEMILLA,
        "fecha_referencia": FECHA_REFERENCIA.isoformat(),
        **asdict(PARAMETROS),
    }


def main() -> None:
    """Imprime el escenario en JSON para su inspección y registro de evidencias."""
    print(json.dumps(resumen_escenario(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

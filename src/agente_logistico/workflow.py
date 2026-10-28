"""Workflow LangGraph del compromiso de entrega: orquesta RAG, SQL y reglas."""

import inspect
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import rag, servicios
from .config_caso import FECHA_REFERENCIA, PARAMETROS
from .estado_workflow import (
    EstadoLogistico,
    EstadoProceso,
    SolicitudLogistica,
    estado_inicial,
)
from .reglas import DecisionCompromiso, evaluar_compromiso
from .reintento import acon_reintento, con_reintento, simular_fallo_transitorio

Extractor = Callable[[str], "SolicitudLogistica | Awaitable[SolicitudLogistica]"]
Embedder = Callable[[list[str], str], list[list[float]]]

CONSULTA_POLITICA = (
    "ventana de entrega estándar, despacho extraordinario, "
    "costo y aprobación del supervisor de logística"
)


def extractor_llm() -> Extractor:
    """Crea el extractor de producción; requiere PROVIDER_API_KEY configurada."""
    from agents import Agent, Runner

    from .modelo import build_model

    agente = Agent(
        name="Extractor de solicitudes LOG-001",
        model=build_model(),
        instructions=(
            "Extrae la solicitud de compromiso de entrega del mensaje del usuario. "
            f"La fecha de referencia del escenario es {FECHA_REFERENCIA.isoformat()}; "
            "convierte fechas relativas a formato ISO. Si falta el almacén, usa ALM-LIM."
        ),
        output_type=SolicitudLogistica,
    )

    async def extraer(texto: str) -> SolicitudLogistica:
        """Ejecuta el agente extractor y devuelve la solicitud tipada."""
        resultado = await Runner.run(agente, texto)
        return resultado.final_output

    return extraer


def _serializar_evaluacion(evaluacion) -> dict[str, Any]:
    """Convierte la evaluación de reglas en un dict JSON serializable."""
    datos = asdict(evaluacion)
    datos["decision"] = evaluacion.decision.value
    datos["tipo_despacho"] = evaluacion.tipo_despacho.value
    datos["fecha_minima_normal"] = evaluacion.fecha_minima_normal.isoformat()
    return datos


def build_workflow(
    *,
    extractor: Extractor | None = None,
    embedder: Embedder | None = None,
    ruta_bd: Path | str | None = None,
    rag_cache: Path | None = None,
    checkpointer: Any = None,
):
    """Construye el grafo compilado con dependencias inyectables para pruebas."""

    async def extraer_solicitud(estado: EstadoLogistico) -> dict:
        """Estructura y valida la solicitud; si falla, deriva a aclaración."""
        try:
            if estado.get("solicitud"):
                solicitud = SolicitudLogistica.model_validate(estado["solicitud"])
            else:
                if extractor is None:
                    raise ValueError(
                        "No hay extractor configurado: usa entrada estructurada "
                        "o configura PROVIDER_API_KEY para el extractor con LLM."
                    )

                async def _invocar_extractor():
                    """Invoca el extractor admitiendo implementaciones sync o async."""
                    salida = extractor(estado["solicitud_original"])
                    if inspect.isawaitable(salida):
                        salida = await salida
                    return salida

                resultado = await acon_reintento(
                    _invocar_extractor,
                    descripcion="extracción de solicitud",
                )
                solicitud = SolicitudLogistica.model_validate(resultado)
        except Exception as exc:
            return {
                "solicitud": None,
                "estado": EstadoProceso.ACLARACION.value,
                "mensaje": f"No pude estructurar la solicitud: {exc}",
            }
        return {
            "solicitud": solicitud.model_dump(mode="json"),
            "mensaje": (
                f"Solicitud estructurada: {solicitud.cantidad} x {solicitud.sku} "
                f"para {solicitud.cliente_id} el {solicitud.fecha_entrega.isoformat()}."
            ),
        }

    async def cargar_datos_operativos(estado: EstadoLogistico) -> dict:
        """Consulta cliente e inventario; un dato inválido cierra con rechazo."""
        solicitud = SolicitudLogistica.model_validate(estado["solicitud"])
        cliente = servicios.consultar_cliente(solicitud.cliente_id, ruta_bd)
        if not cliente["ok"]:
            return {
                "estado": EstadoProceso.RECHAZADO.value,
                "mensaje": cliente["message"],
            }
        if cliente["cliente"]["estado"] != "activo":
            return {
                "cliente": cliente["cliente"],
                "estado": EstadoProceso.RECHAZADO.value,
                "mensaje": (
                    f"El cliente {solicitud.cliente_id} está "
                    f"{cliente['cliente']['estado']}; no se puede confirmar."
                ),
                "fuentes": [cliente["source_ref"]],
            }
        disponibilidad = servicios.consultar_disponibilidad(
            solicitud.sku, solicitud.cantidad, ruta_bd
        )
        if not disponibilidad["ok"]:
            return {
                "cliente": cliente["cliente"],
                "estado": EstadoProceso.RECHAZADO.value,
                "mensaje": disponibilidad["message"],
                "fuentes": [cliente["source_ref"]],
            }
        return {
            "cliente": cliente["cliente"],
            "stock_disponible": disponibilidad["stock_disponible"],
            "fuentes": [cliente["source_ref"], disponibilidad["source_ref"]],
        }

    async def consultar_capacidad(estado: EstadoLogistico) -> dict:
        """Consulta la capacidad con retry ante fallos transitorios (429/503/red)."""
        solicitud = SolicitudLogistica.model_validate(estado["solicitud"])

        def _consultar() -> dict:
            """Envuelve la simulación de fallo y la consulta parametrizada."""
            simular_fallo_transitorio(estado["id_solicitud"])
            return servicios.consultar_capacidad_despacho(
                solicitud.fecha_entrega.isoformat(),
                solicitud.cantidad,
                solicitud.almacen,
                ruta_bd,
            )

        capacidad = con_reintento(_consultar, descripcion="capacidad de despacho")
        if not capacidad["ok"]:
            return {
                "estado": EstadoProceso.RECHAZADO.value,
                "mensaje": capacidad["message"],
            }
        return {"capacidad": capacidad, "fuentes": [capacidad["source_ref"]]}

    async def recuperar_politica(estado: EstadoLogistico) -> dict:
        """Recupera las políticas con retry; sin API registra la degradación."""
        try:
            resultados = con_reintento(
                lambda: rag.search(
                    CONSULTA_POLITICA,
                    top_k=2,
                    embedder=embedder,
                    cache_path=rag_cache or rag.CACHE_PATH,
                ),
                descripcion="recuperación de políticas",
            )
        except Exception as exc:
            return {
                "mensaje": f"Políticas no recuperadas ({exc}); las reglas deterministas deciden.",
            }
        if not resultados:
            return {"mensaje": "Sin evidencia documental suficiente; las reglas deciden."}
        return {"fuentes": [item["source_ref"] for item in resultados]}

    async def evaluar_reglas(estado: EstadoLogistico) -> dict:
        """Aplica las reglas deterministas con los datos ya recopilados."""
        solicitud = SolicitudLogistica.model_validate(estado["solicitud"])
        evaluacion = evaluar_compromiso(
            fecha_solicitud=FECHA_REFERENCIA,
            fecha_entrega=solicitud.fecha_entrega,
            cantidad=solicitud.cantidad,
            stock_disponible=estado["stock_disponible"],
            capacidad_diaria=PARAMETROS.capacidad_diaria,
            capacidad_reservada=estado["capacidad"]["capacidad_reservada"],
            ventana_entrega_dias=PARAMETROS.ventana_entrega_dias,
            costo_extraordinario_usd=PARAMETROS.costo_extraordinario_usd,
        )
        return {"evaluacion": _serializar_evaluacion(evaluacion)}

    async def confirmar_compromiso(estado: EstadoLogistico) -> dict:
        """Cierra la confirmación, distinguiendo despacho normal y extraordinario."""
        solicitud = SolicitudLogistica.model_validate(estado["solicitud"])
        evaluacion = estado["evaluacion"]
        if evaluacion["tipo_despacho"] == "extraordinario":
            aprobacion = estado["aprobacion"]
            mensaje = (
                f"Compromiso confirmado con despacho extraordinario: "
                f"{solicitud.cantidad} x {solicitud.sku} para {solicitud.cliente_id} "
                f"el {solicitud.fecha_entrega.isoformat()}. Aprobado por "
                f"{aprobacion['supervisor']}. "
                f"Costo extraordinario: USD {evaluacion['costo_extraordinario_usd']}."
            )
        else:
            mensaje = (
                f"Compromiso confirmado: {solicitud.cantidad} x {solicitud.sku} para "
                f"{solicitud.cliente_id} el {solicitud.fecha_entrega.isoformat()} "
                f"con despacho normal. {evaluacion['motivo']}"
            )
        return {"estado": EstadoProceso.CONFIRMADO.value, "mensaje": mensaje}

    async def marcar_excepcion(estado: EstadoLogistico) -> dict:
        """Publica la excepción como pendiente antes de la pausa humana."""
        evaluacion = estado["evaluacion"]
        return {
            "estado": EstadoProceso.PENDIENTE_APROBACION.value,
            "aprobacion": {
                "requerida": True,
                "rol": "supervisor_logistica",
                "decision": None,
                "supervisor": None,
                "comentario": None,
            },
            "mensaje": (
                f"Excepción pendiente de aprobación del supervisor de logística. "
                f"{evaluacion['motivo']} "
                f"Costo extraordinario: USD {evaluacion['costo_extraordinario_usd']}."
            ),
        }

    async def esperar_aprobacion(estado: EstadoLogistico) -> dict:
        """Pausa el grafo con interrupt() hasta la decisión del supervisor.

        Requiere un checkpointer: la ejecución queda persistida y se reanuda
        con `Command(resume=...)` enviando decision, supervisor y comentario.
        """
        evaluacion = estado["evaluacion"]
        decision = interrupt(
            {
                "tipo": "aprobacion_supervisor",
                "id_solicitud": estado["id_solicitud"],
                "motivo": evaluacion["motivo"],
                "costo_extraordinario_usd": evaluacion["costo_extraordinario_usd"],
                "rol_requerido": "supervisor_logistica",
            }
        )
        return {
            "aprobacion": {
                "requerida": True,
                "rol": "supervisor_logistica",
                "decision": decision.get("decision"),
                "supervisor": decision.get("supervisor"),
                "comentario": decision.get("comentario"),
            },
            "mensaje": (
                f"Excepción {decision.get('decision')} por "
                f"{decision.get('supervisor', 'supervisor_logistica')}."
            ),
        }

    async def cerrar_rechazo(estado: EstadoLogistico) -> dict:
        """Cierra la ruta de rechazo con el motivo de negocio correspondiente."""
        aprobacion = estado.get("aprobacion")
        if aprobacion and aprobacion.get("decision") == "rechazado":
            motivo = (
                f"El supervisor {aprobacion.get('supervisor')} no aprobó el "
                f"despacho extraordinario. {aprobacion.get('comentario') or ''}"
            ).strip()
        elif estado.get("evaluacion"):
            motivo = estado["evaluacion"]["motivo"]
        else:
            motivo = estado["mensaje"]
        return {
            "estado": EstadoProceso.RECHAZADO.value,
            "mensaje": f"Compromiso rechazado. {motivo}",
        }

    async def cerrar_aclaracion(estado: EstadoLogistico) -> dict:
        """Cierra sin tools cuando la solicitud no pudo estructurarse."""
        return {
            "estado": EstadoProceso.ACLARACION.value,
            "mensaje": (
                f"{estado['mensaje']} Indica cliente, SKU, cantidad y fecha de entrega."
            ),
        }

    def ruta_tras_extraccion(estado: EstadoLogistico) -> str:
        """Deriva a aclaración si la solicitud no quedó estructurada."""
        if estado["estado"] == EstadoProceso.ACLARACION.value:
            return "cerrar_aclaracion"
        return "cargar_datos_operativos"

    def ruta_tras_datos(estado: EstadoLogistico) -> str:
        """Interrumpe la cadena cuando un dato operativo ya impide el compromiso."""
        if estado["estado"] == EstadoProceso.RECHAZADO.value:
            return "cerrar_rechazo"
        return "consultar_capacidad"

    def ruta_tras_evaluacion(estado: EstadoLogistico) -> str:
        """Enruta según la decisión determinista de las reglas de negocio."""
        decision = estado["evaluacion"]["decision"]
        if decision == DecisionCompromiso.DIRECTO.value:
            return "confirmar_compromiso"
        if decision == DecisionCompromiso.REQUIERE_APROBACION.value:
            return "marcar_excepcion"
        return "cerrar_rechazo"

    def ruta_tras_excepcion(estado: EstadoLogistico) -> str:
        """Enruta según la decisión humana registrada tras el interrupt."""
        if estado["aprobacion"].get("decision") == "aprobado":
            return "confirmar_compromiso"
        return "cerrar_rechazo"

    grafo = StateGraph(EstadoLogistico)
    grafo.add_node("extraer_solicitud", extraer_solicitud)
    grafo.add_node("cargar_datos_operativos", cargar_datos_operativos)
    grafo.add_node("consultar_capacidad", consultar_capacidad)
    grafo.add_node("recuperar_politica", recuperar_politica)
    grafo.add_node("evaluar_reglas", evaluar_reglas)
    grafo.add_node("confirmar_compromiso", confirmar_compromiso)
    grafo.add_node("marcar_excepcion", marcar_excepcion)
    grafo.add_node("esperar_aprobacion", esperar_aprobacion)
    grafo.add_node("cerrar_rechazo", cerrar_rechazo)
    grafo.add_node("cerrar_aclaracion", cerrar_aclaracion)

    grafo.add_edge(START, "extraer_solicitud")
    grafo.add_conditional_edges("extraer_solicitud", ruta_tras_extraccion)
    grafo.add_conditional_edges("cargar_datos_operativos", ruta_tras_datos)
    grafo.add_edge("consultar_capacidad", "recuperar_politica")
    grafo.add_edge("recuperar_politica", "evaluar_reglas")
    grafo.add_conditional_edges("evaluar_reglas", ruta_tras_evaluacion)
    grafo.add_edge("marcar_excepcion", "esperar_aprobacion")
    grafo.add_conditional_edges("esperar_aprobacion", ruta_tras_excepcion)
    grafo.add_edge("confirmar_compromiso", END)
    grafo.add_edge("cerrar_rechazo", END)
    grafo.add_edge("cerrar_aclaracion", END)
    return grafo.compile(checkpointer=checkpointer)


async def ejecutar_workflow(
    solicitud_original: str,
    *,
    solicitud: SolicitudLogistica | dict | None = None,
    id_solicitud: str | None = None,
    extractor: Extractor | None = None,
    embedder: Embedder | None = None,
    ruta_bd: Path | str | None = None,
    rag_cache: Path | None = None,
    checkpointer: Any = None,
) -> EstadoLogistico:
    """Ejecuta el workflow y devuelve el estado final (o pausado por HITL).

    Con `checkpointer`, el `id_solicitud` actúa como hilo persistente: una
    excepción queda pausada en `interrupt()` hasta `reanudar_workflow`.
    """
    grafo = build_workflow(
        extractor=extractor,
        embedder=embedder,
        ruta_bd=ruta_bd,
        rag_cache=rag_cache,
        checkpointer=checkpointer,
    )
    inicial = estado_inicial(
        solicitud_original, id_solicitud or f"SOL-{uuid.uuid4().hex[:8].upper()}"
    )
    if solicitud is not None:
        inicial["solicitud"] = (
            solicitud.model_dump(mode="json")
            if isinstance(solicitud, SolicitudLogistica)
            else dict(solicitud)
        )
    config = {"configurable": {"thread_id": inicial["id_solicitud"]}}
    return await grafo.ainvoke(inicial, config=config)


async def reanudar_workflow(
    id_solicitud: str,
    *,
    decision: str,
    supervisor: str,
    comentario: str = "",
    extractor: Extractor | None = None,
    embedder: Embedder | None = None,
    ruta_bd: Path | str | None = None,
    rag_cache: Path | None = None,
    checkpointer: Any,
) -> EstadoLogistico:
    """Reanuda un hilo pausado en HITL con la decisión del supervisor."""
    if decision not in ("aprobado", "rechazado"):
        raise ValueError("La decisión debe ser 'aprobado' o 'rechazado'")
    grafo = build_workflow(
        extractor=extractor,
        embedder=embedder,
        ruta_bd=ruta_bd,
        rag_cache=rag_cache,
        checkpointer=checkpointer,
    )
    config = {"configurable": {"thread_id": id_solicitud}}
    comando = Command(
        resume={
            "decision": decision,
            "supervisor": supervisor,
            "comentario": comentario,
        }
    )
    return await grafo.ainvoke(comando, config=config)

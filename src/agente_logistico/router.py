"""Router determinista, por modelo e híbrido para las rutas del agente."""

import re

from agents import Agent, Runner

from .contratos import Route, RouteDecision
from .modelo import build_model


class DeterministicRouter:
    """Aplica reglas auditables para consultas logísticas frecuentes."""

    def route(self, query: str) -> RouteDecision:
        """Clasifica una consulta sin llamar a herramientas ni servicios externos."""
        texto = query.lower().strip()
        if len(texto) < 4:
            return RouteDecision(
                route=Route.CLARIFY,
                confidence=0.99,
                reason="Consulta demasiado corta",
                clarification_question="¿Puedes describir qué necesitas consultar?",
            )

        terminos_documentales = [
            "política",
            "politica",
            "procedimiento",
            "sla",
            "ventana",
            "días hábiles",
            "dias habiles",
            "aprobación",
            "aprobacion",
        ]
        terminos_operativos = [
            "stock",
            "existencias",
            "disponibilidad",
            "capacidad",
            "cliente",
            "sku",
            "inventario",
        ]
        if any(t in texto for t in terminos_documentales) and any(t in texto for t in terminos_operativos):
            return RouteDecision(
                route=Route.CLARIFY,
                confidence=0.88,
                reason="La consulta mezcla política documental con datos operacionales",
                clarification_question="¿Necesitas la política, el dato operacional actual o ambos por separado?",
            )

        acciones_proceso = ["evalúa", "evalua", "evaluar", "confirma", "confirmar", "comprometer", "programar"]
        tiene_cliente = re.search(r"C-\d{4}", query.upper()) is not None
        tiene_cantidad = re.search(r"\b\d+\s*(unidades|uds|equipos)?\b", texto) is not None
        if any(accion in texto for accion in acciones_proceso) and tiene_cliente and tiene_cantidad:
            return RouteDecision(
                route=Route.WORKFLOW,
                confidence=0.96,
                reason="Solicitud de evaluación o confirmación de entrega con proceso de varios pasos",
            )

        if any(t in texto for t in terminos_documentales) or "despacho extraordinario" in texto:
            return RouteDecision(route=Route.RAG, confidence=0.95, reason="Pregunta sobre política o procedimiento documental")

        terminos_historicos = ["ventas", "vendimos", "histórico", "historico", "facturación", "facturacion", "ingresos", "trimestre"]
        if any(t in texto for t in terminos_historicos):
            return RouteDecision(route=Route.SQL, confidence=0.95, reason="Consulta histórica o agregada sobre ventas")

        texto_conceptual = texto.lstrip("¿?¡!")
        if texto_conceptual.startswith(("qué significa", "que significa", "define", "qué es un", "que es un")):
            return RouteDecision(route=Route.DIRECT, confidence=0.90, reason="Pregunta conceptual sin datos internos")

        if "stock" in texto and not re.search(r"[A-Z]{2,}-[A-Z0-9-]+", query.upper()):
            return RouteDecision(
                route=Route.CLARIFY,
                confidence=0.95,
                reason="Falta el SKU para consultar stock",
                clarification_question="¿Qué SKU debo consultar?",
            )
        if any(t in texto for t in terminos_operativos):
            return RouteDecision(route=Route.TOOLS, confidence=0.92, reason="Dato operacional actual acotado")

        return RouteDecision(
            route=Route.CLARIFY,
            confidence=0.55,
            reason="No existe una regla de alta confianza",
            clarification_question="¿Puedes indicar cliente, SKU, cantidad, fecha o el tipo de información buscada?",
        )


class ModelRouter:
    """Usa el LLM únicamente como clasificador semántico con salida validada."""

    def __init__(self) -> None:
        """Configura el clasificador sin habilitar herramientas."""
        self.agent = Agent(
            name="Router Logístico LOG-001",
            model=build_model(),
            instructions=(
                "Clasifica la consulta en exactamente una ruta. "
                "rag=políticas o procedimientos; sql=historial o agregados; "
                "tools=cliente, stock, SKU o capacidad actual; workflow=evaluar o confirmar "
                "un compromiso de entrega; direct=concepto general; clarify=información esencial "
                "faltante o ambigua. No respondas la consulta ni inventes datos."
            ),
            output_type=RouteDecision,
        )

    async def route(self, query: str) -> RouteDecision:
        """Ejecuta la clasificación con el modelo configurado."""
        resultado = await Runner.run(self.agent, query)
        return resultado.final_output


class HybridRouter:
    """Prioriza reglas y consulta al modelo solo bajo el umbral de confianza."""

    def __init__(self, threshold: float = 0.90) -> None:
        """Crea el router híbrido con su umbral de fallback."""
        self.rules = DeterministicRouter()
        self.model = ModelRouter()
        self.threshold = threshold

    async def route(self, query: str) -> RouteDecision:
        """Devuelve la regla de alta confianza o delega la clasificación semántica."""
        decision = self.rules.route(query)
        if decision.confidence >= self.threshold:
            return decision
        return await self.model.route(query)

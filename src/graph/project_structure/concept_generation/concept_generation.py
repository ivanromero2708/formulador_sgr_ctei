"""
concept_generation_flow.py ─ Versión compacta con parche
que acepta tanto CGState (Pydantic) como dict en runtime.
Mantiene la clase pública `ConceptGenerationFlow`.
"""

# ──────────────────────── imports básicos
from __future__ import annotations
import json
from typing import List, Literal, Dict, Any, Annotated
import operator

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langgraph.types import Command, Send
from langgraph.channels.last_value import LastValue
from langgraph_swarm import create_swarm, SwarmState, create_handoff_tool
from langgraph.prebuilt import create_react_agent

from src.llms.llm import create_llm_model
from src.config.configuration import MultiAgentConfiguration
from src.tools.project_scoring import project_scoring_tool
from src.prompts.prompts_concept_generation import (
    PROMPT_SYSTEM_CONCEPT_GENERATION,
    PROMPT_HUMAN_CONCEPT_GENERATION,
    PROMPT_SYSTEM_CONCEPT_ENRICHMENT,
    PROMPT_SYSTEM_CONCEPT_SCORING,
)
from src.graph.state import (
    FormuladorCTeIAgent,
    ConceptoProyectoGenerado,  # y los otros modelos que ya tienes
)

# ──────────────────────── modelos pydantic
class ConceptosGenerados(BaseModel):
    conceptos: List[ConceptoProyectoGenerado] = Field(default_factory=list)


class CGState(FormuladorCTeIAgent):
    conceptos_enriquecidos: Annotated[ConceptoProyectoGenerado, operator.add] = Field(default_factory=list)


class CGSwarmState(SwarmState):
    structured_response: ConceptoProyectoGenerado | None = None
    concepto: ConceptoProyectoGenerado | None = None  # se pasa 1-a-1


# ──────────────────────── flujo principal
class ConceptGenerationFlow:
    """Pipeline generación–enriquecimiento de conceptos."""

    # — utilidades —
    @staticmethod
    def _jsonable(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return {k: ConceptGenerationFlow._jsonable(v)
                    for k, v in obj.model_dump(exclude_none=True).items()}
        if isinstance(obj, (list, tuple)):
            return [ConceptGenerationFlow._jsonable(x) for x in obj]
        if isinstance(obj, dict):
            return {k: ConceptGenerationFlow._jsonable(v) for k, v in obj.items()}
        return obj

    @staticmethod
    def _build_ctx(state: CGState) -> Dict[str, str]:
        """
        Extrae TODAS las claves esperadas por las plantillas, usando "N/D"
        como valor por defecto cuando falten.
        """
        expected = {
            "perfil_entidades",
            "secciones_tdr",
            "idea_base_proyecto_usuario",
            "demanda_territorial_seleccionada_usuario",
            "presupuesto_estimado_usuario",
            "entidad_proponente_usuario",
            "alianzas_usuario",
            "objetivo_tdr",
            "demanda_territorial_tdr",
            "lineas_tematicas_tdr",
            "criterios_evaluacion_proyectos_tdr",
            "duracion_proyecto_usuario",
            "departamento",
            "reto",
        }

        def to_json(value: Any) -> str:
            return json.dumps(
                ConceptGenerationFlow._jsonable(value),
                indent=2,
                ensure_ascii=False,
            )

        ctx: Dict[str, str] = {
            k: to_json(state[k]) if k in state else "N/D"
            for k in expected
        }
        return ctx

    @staticmethod
    def _agent(name: str, sys_prompt: str, tools: list, llm):
        """Factory genérico para agentes React con salida estructurada."""
        return create_react_agent(
            llm,
            prompt=SystemMessage(content=sys_prompt),
            tools=tools,
            name=name,
            response_format=ConceptoProyectoGenerado,
        )

        # ──────────────────────────────────────────────────────────────
    # Helper estático: convierte un ConceptoProyectoGenerado a texto
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _format_concepto_proyecto(concept: ConceptoProyectoGenerado) -> str:
        """Devuelve una descripción legible del borrador de concepto."""
        if concept is None:
            return "N/D"

        obj_esp = (f"  • {o}" for o in (concept.objetivos_especificos or []))
        res_esp = (f"  • {r}" for r in (concept.resultados_esperados or []))

        linea_tematica = (
            f"{concept.linea_tematica_asociada.macro_linea} – "
            f"{concept.linea_tematica_asociada.sub_linea}"
            if concept.linea_tematica_asociada else "N/D"
        )
        demanda = (
            concept.demanda_territorial_asociada.reto
            if concept.demanda_territorial_asociada else "N/D"
        )

        return (
            f"ID Concepto: {concept.id_concepto}\n"
            f"Título: {concept.titulo_sugerido}\n"
            f"Problema: {concept.problema_abordado}\n"
            f"Objetivo general: {concept.objetivo_general}\n"
            f"Objetivos específicos:\n{obj_esp or '  • N/D'}\n"
            f"Resultados esperados:\n{res_esp or '  • N/D'}\n"
            f"Línea temática: {linea_tematica}\n"
            f"Demanda territorial asociada: {demanda}\n"
            f"Presupuesto SGR estimado: {concept.presupuesto_estimado_sgr or 'N/D'}\n"
            f"Duración (meses): {concept.duracion_estimada_meses or 'N/D'}"
        )

    # ──────────────────────────────────────────────────────────────
    # Nodo “brainstorm” (genera borradores y paraleliza hacia el swarm)
    # ──────────────────────────────────────────────────────────────
    def _brainstorm(self, state: CGState, config: RunnableConfig) -> Command:
        # Modelo estructurado
        llm_struct = (
            create_llm_model(
                MultiAgentConfiguration.from_runnable_config(config).o4mini
            ).with_structured_output(ConceptosGenerados)
        )

        # Contexto para las plantillas
        ctx = self._build_ctx(state)
        res = llm_struct.invoke(
            [
                SystemMessage(content=PROMPT_SYSTEM_CONCEPT_GENERATION.format(**ctx)),
                HumanMessage(content=PROMPT_HUMAN_CONCEPT_GENERATION.format(**ctx)),
            ]
        )

        secciones: list = state.get("secciones_tdr", [])

        demanda_territorial_tdr_str = next(
            (s.contenido for s in secciones if s.nombre == "demandas_territoriales_tdr"),
            "N/D",
        )
        lineas_tematicas_tdr_str = next(
            (s.contenido for s in secciones if s.nombre == "lineas_tematicas_tdr"),
            "N/D",
        )
        criterios_evaluacion_tdr_str = next(
            (s.contenido for s in secciones if s.nombre == "criterios_evaluacion_proyectos_tdr"),
            "N/D",
        )

        # Paraleliza: un Send por cada borrador
        goto = [
            Send(
                "swarm",
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Procede con el proceso de enriquecimiento y evaluación "
                                "del siguiente proyecto:\n\n"
                                f"{self._format_concepto_proyecto(concept)}\n\n"
                                "Es muy importante que tengas en cuenta las demandas "
                                "territoriales de los términos de referencia:\n\n"
                                f"<demanda_territorial_tdr>{demanda_territorial_tdr_str}"
                                "</demanda_territorial_tdr>\n\n"
                                "Las líneas temáticas del TDR son las siguientes:\n\n"
                                f"<lineas_tematicas_tdr>{lineas_tematicas_tdr_str}"
                                "</lineas_tematicas_tdr>\n\n"
                                "Los criterios de evaluación para los proyectos son:\n\n"
                                f"<criterios_evaluacion_proyectos_tdr>{criterios_evaluacion_tdr_str}"
                                "</criterios_evaluacion_proyectos_tdr>"
                            ),
                        }
                    ],
                    "concepto": concept,  # Cada hilo recibe su propio borrador
                },
            )
            for concept in res.conceptos
        ]

        return Command(goto=goto)



    def _swarm_node(
        self, swarm_state: CGSwarmState, config: RunnableConfig
    ) -> Dict[str, Any]:
        cfgs = MultiAgentConfiguration.from_runnable_config(config)
        llm = create_llm_model(cfgs.gpt41mini)

        enrich = self._agent(
            "concept_enrichment_agent",
            PROMPT_SYSTEM_CONCEPT_ENRICHMENT,
            [create_handoff_tool(agent_name="concept_scoring_agent", description="Transferir al agente de Puntuación de Conceptos para evaluar el concepto enriquecido.")],
            llm,
        )

        score = self._agent(
            "concept_scoring_agent",
            PROMPT_SYSTEM_CONCEPT_SCORING,
            [
                create_handoff_tool(agent_name="concept_enrichment_agent", description="Devolver al agente de Enriquecimiento de Conceptos si el concepto necesita mayor refinamiento tras la evaluación."),
                project_scoring_tool,
            ],
            llm,
        )

        swarm = (
            create_swarm(
                [enrich, score],
                default_active_agent="concept_enrichment_agent",
                state_schema=CGSwarmState,
            )
            .compile()
        )

        res = swarm.invoke(swarm_state, config)
        return {"conceptos_enriquecidos": [res["structured_response"]]}
    
    # ——————————————————— public API
    def __init__(self):
        # armamos el grafo sólo una vez
        
        g = StateGraph(CGState)
        g.add_node("brainstorm", self._brainstorm)
        g.add_node("swarm", self._swarm_node)
        g.add_edge("brainstorm", "swarm")
        g.set_entry_point("brainstorm")        
        self._graph = g.compile()

    def run(
        self, state: CGState, config: RunnableConfig | None = None
    ) -> Command[Literal["__end__"]]:
        result = self._graph.invoke(state, config or RunnableConfig())
        return Command(
            update={
                "conceptos_enriquecidos": result.get("conceptos_enriquecidos", []),
                "messages": result.get("messages", []) + [HumanMessage(content="Subgrafo de generación de conceptos completado.")],
                "perfil_entidades": result.get("perfil_entidades", []),
                },
            goto="__end__",
        )

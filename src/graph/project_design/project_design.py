from langchain_core.messages import HumanMessage
from langgraph.types import Command
from typing import Literal
from pydantic import BaseModel, Field

from ..state import FormuladorCTeIAgent
from src.config.configuration import MultiAgentConfiguration
from src.graph.project_design.deep_research_marco_conceptual.deep_research_marco_conceptual import DeepResearchMarcoConceptual

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langgraph.types import Command





class ProjectDesignState(FormuladorCTeIAgent):
    marco_conceptual: str = Field(..., description="Marco conceptual del proyecto")

class ProjectDesign:
    def __init__(self) -> None:
        self.deep_research_marco_conceptual = DeepResearchMarcoConceptual()
        pass
    
    def desarrollo_cadena_valor(self, state, config) -> Command[Literal["metodologia_proyecto"]]:
        return Command(
            goto="metodologia_proyecto",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Cadena de valor desarrollada")],
            }
        )
    
    def metodologia_proyecto(self, state, config) -> Command[Literal["desarrollo_talento_humano"]]:
        return Command(
            goto="desarrollo_talento_humano",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Metodologia del proyecto desarrollada")],
            }
        )
    
    def desarrollo_talento_humano(self, state, config) -> Command[Literal["definir_productos_esperados"]]:
        return Command(
            goto="definir_productos_esperados",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Talento humano desarrollado")],
            }
        )
    
    def definir_productos_esperados(self, state, config) -> Command[Literal["definir_indicadores_gestion"]]:
        return Command(
            goto="definir_indicadores_gestion",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Productos esperados definidos")],
            }
        )
    
    def definir_indicadores_gestion(self, state, config) -> Command[Literal["definir_aspectos_eticos"]]:
        return Command(
            goto="definir_aspectos_eticos",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Indicadores de gestion definidos")],
            }
        )
    
    def definir_aspectos_eticos(self, state, config) -> Command[Literal["analisis_licencias_permisos"]]:
        return Command(
            goto="analisis_licencias_permisos",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Aspectos eticos definidos")],
            }
        )
    
    def analisis_licencias_permisos(self, state, config) -> Command[Literal["__end__"]]:
        return Command(
            goto="__end__",
            update={
                "messages": state.get("messages", []) + [HumanMessage(content="Analisis de licencias y permisos completado")],
            }
        )
    
    def grafo_diseño_proyecto(self):
        builder = StateGraph(ProjectDesignState)
        builder.set_entry_point("desarrollo_marco_conceptual")
        builder.add_node("desarrollo_marco_conceptual", self.deep_research_marco_conceptual.run)
        builder.add_node("desarrollo_cadena_valor", self.desarrollo_cadena_valor)
        builder.add_node("metodologia_proyecto", self.metodologia_proyecto)
        builder.add_node("desarrollo_talento_humano", self.desarrollo_talento_humano)
        builder.add_node("definir_productos_esperados", self.definir_productos_esperados)
        builder.add_node("definir_indicadores_gestion", self.definir_indicadores_gestion)
        builder.add_node("definir_aspectos_eticos", self.definir_aspectos_eticos)
        builder.add_node("analisis_licencias_permisos", self.analisis_licencias_permisos)
        return builder.compile()
    
    def run(self, state: ProjectDesignState, config: RunnableConfig) -> Command[Literal["policy_alignment_justification"]]:
        graph = self.grafo_diseño_proyecto()
        
        invoke_config = config.copy() if config else {}
        invoke_config["recursion_limit"] = 300
        
        result = graph.invoke(state, invoke_config)
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Diseño del proyecto terminado")],
                "marco_conceptual": result["marco_conceptual"],
            },
            goto="policy_alignment_justification"
        )
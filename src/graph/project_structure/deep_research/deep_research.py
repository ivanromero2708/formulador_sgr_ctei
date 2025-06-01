from langgraph_swarm.handoff import create_handoff_tool
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_swarm
from langchain_core.messages import SystemMessage, HumanMessage

from src.graph.state import FormuladorCTeIAgent, PerfilEntidad, SeccionTDR, EntidadProponente, Alianza, IdeaProyecto, DemandaTerritorial
from src.config.configuration import MultiAgentConfiguration
from src.prompts.prompts_concept_generation import PROMPT_SYSTEM_PLANNER, PROMPT_SYSTEM_WEB_RESEARCH
from src.llms.llm import create_llm_model
from src.tools.serper_dev_tool import serper_dev_search_tool
from src.tools.web_rag_pipeline import web_rag_pipeline_tool


from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict # Added Dict for potential state update return type




class PerfilEntidades(BaseModel):
    perfil_entidades: List[PerfilEntidad] = Field(default_factory=list, description="Perfil de entidades relevantes")

class ConsultasPlanner(BaseModel):
    consultas_investigacion: List[str] = Field(default_factory=list, description="Consultas de investigación para investigador web")

class ContextResearchSwarmState(FormuladorCTeIAgent):
    active_agent: Optional[str]
    consultas_investigacion: List[str] = Field(default_factory=list, description="Consultas de investigación para investigador web")
    structured_response: Optional[PerfilEntidades] = Field(default=None, description="Perfil de Entidades relevantes")

# Definir herramientas de transferencia
hand_off_to_web_research = create_handoff_tool(
    agent_name="web_research_agent",
    description="Transferir al agente de investigación web para recopilar información detallada basada en el plan de investigación."
)

hand_off_to_planner = create_handoff_tool(
    agent_name="planner_research_agent",
    description="Transferir de nuevo al agente planificador si se necesita una planificación adicional o refinamiento de consultas, o si la investigación está completa."
)

class DeepResearchEntidades:
    @staticmethod
    def _get_seccion_content(secciones: List[SeccionTDR], nombre_seccion: str, default_val: str = "No disponible") -> str:
        if not secciones:
            return default_val
        for seccion in secciones:
            if seccion.nombre == nombre_seccion:
                return seccion.contenido
        return default_val

    @staticmethod
    def _format_entidad_proponente(entidad: Optional[EntidadProponente]) -> str:
        if not entidad:
            return "No disponible"
        return f"Nombre: {entidad.nombre}, Tipo: {entidad.tipo or 'N/A'}"

    @staticmethod
    def _format_alianzas(alianzas: Optional[List[Alianza]]) -> str:
        if not alianzas:
            return "No hay alianzas especificadas."
        alianzas_info_list = [
            f"  - Nombre: {a.nombre}, Rol: {a.rol}, Tipo: {a.tipo or 'N/A'}"
            for a in alianzas
        ]
        return "\n".join(alianzas_info_list)

    @staticmethod
    def _format_idea_proyecto(idea: Optional[IdeaProyecto]) -> str:
        if not idea:
            return "No disponible"
        return f"Título Provisional: {idea.titulo_provisional}\nProblema: {idea.problema_descripcion}\nTecnología/Enfoque: {idea.tecnologia_enfoque_propuesto}"

    @staticmethod
    def _format_demanda_territorial(demanda: Optional[DemandaTerritorial]) -> str:
        if not demanda:
            return "No disponible"
        return f"ID: {demanda.ID or 'N/A'}\nDepartamento: {demanda.departamento or 'N/A'}\nReto: {demanda.reto}\nDemanda Territorial: {demanda.demanda_territorial}"

    def __init__(self):
        self.TOOLS_PLANNER = [hand_off_to_web_research]
        self.TOOLS_WEB_RESEARCH = [serper_dev_search_tool, web_rag_pipeline_tool, hand_off_to_planner]
    
    def create_planner_research_agent(self, state: ContextResearchSwarmState, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_model = create_llm_model(agent_configuration.o4mini)
        
        # Prepare string representations of state variables
        entidad_proponente_str = self._format_entidad_proponente(state["entidad_proponente_usuario"])
        alianzas_str = self._format_alianzas(state["alianzas_usuario"])
        entidades_info_str = f"Entidad Proponente:\n{entidad_proponente_str}\n\nEntidades Aliadas:\n{alianzas_str}"

        objetivo_tdr_str = self._get_seccion_content(state["secciones_tdr"], "objetivo_tdr")
        departamento_str = state["departamento"] if state["departamento"] else "No disponible"
        
        reto_usuario_str = state["demanda_territorial_seleccionada_usuario"].reto if state["demanda_territorial_seleccionada_usuario"].reto else "No disponible"
        
        demanda_territorial_tdr_str = self._get_seccion_content(state["secciones_tdr"], "demandas_territoriales_tdr")
        lineas_tematicas_tdr_str = self._get_seccion_content(state["secciones_tdr"], "lineas_tematicas_tdr")
        
        idea_base_proyecto_str = self._format_idea_proyecto(state["idea_base_proyecto_usuario"])
        demanda_seleccionada_str = self._format_demanda_territorial(state["demanda_territorial_seleccionada_usuario"])

        agent_prompt = SystemMessage(
            content=PROMPT_SYSTEM_PLANNER.format(
                entidades=entidades_info_str,
                objetivo_tdr=objetivo_tdr_str,
                departamento=departamento_str,
                reto=reto_usuario_str, # Using specific user's selected reto
                demanda_territorial_tdr=demanda_territorial_tdr_str,
                lineas_tematicas_tdr=lineas_tematicas_tdr_str,
                idea_base_proyecto_usuario=idea_base_proyecto_str,
                demanda_territorial_seleccionada_usuario=demanda_seleccionada_str,
            )
        )
        
        agent_builder = create_react_agent(
            llm_model,
            tools=self.TOOLS_PLANNER,
            prompt=agent_prompt,
            name="planner_research_agent",
            response_format=ConsultasPlanner,
        )
        return agent_builder        
    
    def create_web_research_agent(self, state: ContextResearchSwarmState, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_model = create_llm_model(agent_configuration.gpt41mini)
        
        # Prepare string representations of state variables
        entidad_proponente_str = self._format_entidad_proponente(state["entidad_proponente_usuario"])
        alianzas_str = self._format_alianzas(state["alianzas_usuario"])
        entidades_info_str = f"Entidad Proponente:\n{entidad_proponente_str}\n\nEntidades Aliadas:\n{alianzas_str}"

        objetivo_tdr_str = self._get_seccion_content(state["secciones_tdr"], "objetivo_tdr")
        departamento_str = state["departamento"] if state["departamento"] else "No disponible"

        agent_prompt = SystemMessage(
            content=PROMPT_SYSTEM_WEB_RESEARCH.format(
                entidades=entidades_info_str,
                objetivo_tdr=objetivo_tdr_str,
                departamento=departamento_str,
            )
        )
        
        agent_builder = create_react_agent(
            llm_model,
            tools=self.TOOLS_WEB_RESEARCH,
            prompt=agent_prompt,
            name="web_research_agent",
            response_format=PerfilEntidades,
        )
        return agent_builder
    
    def create_context_swarm(self, state: ContextResearchSwarmState, config: RunnableConfig):
        context_research_builder = create_swarm(
            [
                self.create_planner_research_agent(state, config),
                self.create_web_research_agent(state, config),
            ],
            default_active_agent = "planner_research_agent",
            state_schema=ContextResearchSwarmState,
        )        
        return context_research_builder.compile()
    
    def run(self, state_dict: dict, config: RunnableConfig) -> Command[Literal["concept_generation_node"]]:
        context_swarm_graph = self.create_context_swarm(state_dict, config) 
        final_swarm_state_dict = context_swarm_graph.invoke(state_dict, config) # input is FormuladorCTeIAgent dict
        
        structured_response_agent = final_swarm_state_dict.get("structured_response")
        
        perfil_entidades = structured_response_agent.perfil_entidades
        
        current_messages = state_dict.get("messages", [])
        if not isinstance(current_messages, list):
            current_messages = list(current_messages) if isinstance(current_messages, (tuple, set)) else []

        new_message = HumanMessage(
            content="Perfil de entidades del proyecto completado por el swarm de investigación profunda.",
            name="context_deep_research_swarm",
        )
        updated_messages = current_messages + [new_message]

        update_for_parent_state = {
            "messages": updated_messages,
            "perfil_entidades": perfil_entidades, # Updates FormuladorCTeIAgent.perfil_entidades
        }
        
        return Command(
            update=update_for_parent_state,
            goto="concept_generation_node" # Ensures flow to the correct next node
        )
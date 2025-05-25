from langgraph_swarm.handoff import create_handoff_tool # Added import
from langgraph.types import Send # Command removed as it's custom and not used in this revision
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_swarm
from langchain_core.messages import SystemMessage, HumanMessage

from src.graph.state import FormuladorCTeIAgent
from src.config.configuration import MultiAgentConfiguration
from src.prompts.prompts_concept_generation import PROMPT_SYSTEM_PLANNER, PROMPT_SYSTEM_WEB_RESEARCH
from src.llms.llm import create_llm_model

from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict # Added Dict for potential state update return type


class PerfilEntidad(BaseModel):
    nombre: str = Field(description="Nombre de la entidad")
    tipo: Literal["Proponente", "Aliado"] = Field(description="Tipo de entidad")
    
    areas_expertise_relevante: List[str] = Field(default_factory=list, description="Áreas de expertise relevantes")
    capacidades_tecnicas: List[str] = Field(default_factory=list, description="Capacidades técnicas relevantes")
    lineas_investigacion_relevantes: List[str] = Field(default_factory=list, description="Líneas de investigación relevantes de la institución")
    logros_relevantes: List[str] = Field(default_factory=list, description="Logros relevantes de la institución relacionados con las líneas temáticas del proyecto")
    
    experiencia_proyectos_relacionados: List[str] = Field(default_factory=list, description="Experiencia en proyectos relacionados")

class PerfilEntidades(BaseModel):
    perfil_entidades: List[PerfilEntidad] = Field(default_factory=list, description="Perfil de entidades relevantes")

class ConsultasPlanner(BaseModel):
    consultas_investigacion: List[str] = Field(default_factory=list, description="Consultas de investigación para investigador web")

class ContextResearchSwarmState(FormuladorCTeIAgent):
    active_agent: Optional[str]
    consultas_investigacion: List[str] = Field(default_factory=list, description="Consultas de investigación para investigador web")
    perfil_entidades: PerfilEntidades = Field(default_factory=list, description="Perfil de Entidades relevantes")

# Define Handoff Tools
hand_off_to_web_research = create_handoff_tool(
    agent_name="web_research_agent",
    description="Handoff to the web research agent to gather detailed information based on the research plan."
)

hand_off_to_planner = create_handoff_tool(
    agent_name="planner_research_agent",
    description="Handoff back to the planner agent if further planning or refinement of queries is needed, or if research is complete."
)

class DeepResearchEntidades:
    def __init__(self):
        self.TOOLS_PLANNER = [hand_off_to_web_research]
        self.TOOLS_WEB_RESEARCH = [hand_off_to_planner]
    
    def create_planner_research_agent(self, state: ContextResearchSwarmState, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_model = create_llm_model(agent_configuration.gpt41mini)
        
        agent_prompt = SystemMessage(
            content=PROMPT_SYSTEM_PLANNER.format(
                entidades = state.entidades,
                objetivo_tdr=state.objetivo_tdr,
                departamento = state.departamento,
                reto = state.reto,
                demanda_territorial_tdr = state.demanda_territorial_tdr,
                lineas_tematicas_tdr = state.lineas_tematicas_tdr,
                idea_base_proyecto_usuario = state.idea_base_proyecto_usuario,
                demanda_territorial_seleccionada_usuario = state.demanda_territorial_seleccionada_usuario,
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
        
        agent_prompt = SystemMessage(
            content=PROMPT_SYSTEM_WEB_RESEARCH.format(
                entidades = state.entidades,
                objetivo_tdr=state.objetivo_tdr,
                departamento = state.departamento,
                consultas_investigacion = state.consultas_investigacion,
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
    
    def run(self, state: ContextResearchSwarmState, config: RunnableConfig) -> Command[Literal["generador_conceptos"]]:
        result = self.create_context_swarm(state, config).invoke(state, config)
        perfil_entidades = result["structured_response"].perfil_entidades
        
        return Command(
            update={
            "messages": [
                HumanMessage(
                    content="Se encuentra completado el perfil de las entidades del proyecto.",
                    name="context_deep_research_swarm",
                )
                ],
                "perfil_entidades": perfil_entidades,
            },
            goto="generador_conceptos",
        )
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command, Send
from langgraph_swarm import create_swarm
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph

from src.llms.llm import create_llm_model
from src.config.configuration import MultiAgentConfiguration
from src.graph.project_structure.deep_research.deep_research import PerfilEntidades
from src.graph.state import FormuladorCTeIAgent
from src.prompts.prompts_concept_generation import (
    PROMPT_SYSTEM_CONCEPT_ENRICHMENT, 
    PROMPT_SYSTEM_CONCEPT_SCORING, 
    PROMPT_SYSTEM_CONCEPT_GENERATION,
    PROMPT_HUMAN_CONCEPT_GENERATION
)
from src.graph.state import ConceptoProyectoGenerado

from pydantic import Field
from typing import Optional, List

class ConceptosGenerados(BaseModel):
    conceptos: List[ConceptoProyectoGenerado] = Field(default_factory=list, description="Conceptos generados")
    
class ConceptGenerationState(FormuladorCTeIAgent):
    perfil_entidades: PerfilEntidades = Field(default_factory=list, description="Perfil de Entidades relevantes")
    conceptos: List[ConceptoProyectoGenerado] = Field(default_factory=list, description="Conceptos generados")
    conceptos_enriquecidos: List[ConceptoProyectoGenerado] = Field(default_factory=list, description="Conceptos enriquecidos")
    
class ConceptGenerationSwarm(ConceptGenerationState):
    conceptos_enriquecidos: List[ConceptoProyectoGenerado] = Field(default_factory=list, description="Conceptos enriquecidos")
    active_agent: Optional[str]

class ConceptGenerationFlow:
    def __init__(self):
        self.TOOLS_CONCEPT_ENRICHMENT = [hand_off_to_concept_scoring]
        self.TOOLS_CONCEPT_SCORING = [hand_off_to_concept_enrichment, concept_scoring]
    
    def concept_brainstorm_node(self, state: ConceptGenerationState, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_model = create_llm_model(agent_configuration.o4mini)
        structured_model = llm_model.with_structured_output(ConceptosGenerados)
        
        system_prompt = SystemMessage(
            content=PROMPT_SYSTEM_CONCEPT_GENERATION.format(
                entidades = state.perfil_entidades,
                objetivo_tdr=state.objetivo_tdr,
                departamento = state.departamento,
                reto = state.reto,
                demanda_territorial_tdr = state.demanda_territorial_tdr,
                lineas_tematicas_tdr = state.lineas_tematicas_tdr,
                idea_base_proyecto_usuario = state.idea_base_proyecto_usuario,
                demanda_territorial_seleccionada_usuario = state.demanda_territorial_seleccionada_usuario,
                perfil_entidades = state.perfil_entidades
            )
        )
        
        human_prompt = HumanMessage(
            content = PROMPT_HUMAN_CONCEPT_GENERATION.format(
                idea_base_proyecto_usuario = state.idea_base_proyecto_usuario,
                demanda_territorial_seleccionada_usuario = state.demanda_territorial_seleccionada_usuario,
                perfil_entidades = state.perfil_entidades,
                objetivo_tdr=state.objetivo_tdr,
                departamento = state.departamento,
                reto = state.reto,
                demanda_territorial_tdr = state.demanda_territorial_tdr,
                lineas_tematicas_tdr = state.lineas_tematicas_tdr,
                idea_base_proyecto_usuario = state.idea_base_proyecto_usuario,
                demanda_territorial_seleccionada_usuario = state.demanda_territorial_seleccionada_usuario,
                perfil_entidades = state.perfil_entidades
            )
        )
        
        result = structured_model.invoke([system_prompt, human_prompt])
        
        borrador_conceptos = result.get("conceptos", "")
        
        goto = [
            Send(
                "concept_enrichment_swarm",
                {
                    "borrador_concepto": borrador_concepto,
                    "demanda_territorial_tdr": state.demanda_territorial_tdr,
                    "lineas_tematicas_tdr": state.lineas_tematicas_tdr,
                    "criterios_evaluacion_proyectos_tdr": secciones_tdr["criterios_evaluacion_proyectos_tdr"].contenido
                }
            )
            for borrador_concepto in borrador_conceptos
        ]
        
        return Command(
            goto=goto
        )
    
    def create_concept_enrichment_agent(self, state: ConceptGenerationState, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_model = create_llm_model(agent_configuration.o4mini)
        
        agent_prompt = SystemMessage(
            content=PROMPT_SYSTEM_CONCEPT_ENRICHMENT.format(
                borrador_concepto = state.entidades,
                demanda_territorial_tdr = state.demanda_territorial_tdr,
                lineas_tematicas_tdr = state.lineas_tematicas_tdr,
                demanda_territorial_seleccionada_usuario = state.demanda_territorial_seleccionada_usuario,
            )
        )
        
        agent_builder = create_react_agent(
            llm_model,
            tools=self.TOOLS_CONCEPT_ENRICHMENT,
            prompt=agent_prompt,
            name="concept_enrichment_agent",
            response_format=ConceptosGenerados,
        )
        return agent_builder   
    
    def create_concept_scoring_agent(self, state: ConceptGenerationState, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_model = create_llm_model(agent_configuration.gpt41mini)
        
        agent_prompt = SystemMessage(
            content=PROMPT_SYSTEM_CONCEPT_SCORING.format(
                borrador_concepto = state.entidades,
                demanda_territorial_tdr = state.demanda_territorial_tdr,
                lineas_tematicas_tdr = state.lineas_tematicas_tdr,
                demanda_territorial_seleccionada_usuario = state.demanda_territorial_seleccionada_usuario,
                criterios_evaluacion_proyectos_tdr = state.criterios_evaluacion_proyectos_tdr
            )
        )
        
        agent_builder = create_react_agent(
            llm_model,
            tools=self.TOOLS_CONCEPT_SCORING,
            prompt=agent_prompt,
            name="concept_scoring_agent",
            response_format=ConceptosGenerados,
        )
        return agent_builder   
    
    def create_concept_generation_swarm(self, state: ConceptGenerationSwarm, config: RunnableConfig):
        concept_generation_builder = create_swarm(
            [
                self.create_concept_enrichment_agent(state, config),
                self.create_concept_scoring_agent(state, config),
            ],
            default_active_agent = "concept_enrichment_agent",
            state_schema=ConceptGenerationSwarm,
        )
        concept_generation_graph = concept_generation_builder.compile()

        return concept_generation_graph
    
    def concept_generation_flow(self, state: ConceptGenerationState, config: RunnableConfig):
        
        concept_generation_flow_builder = StateGraph(ConceptGenerationState)
        concept_generation_flow_builder.set_entry_point("concept_brainstorm_node")
        concept_generation_flow_builder.add_node("concept_brainstorm_node", self.concept_brainstorm_node(state, config))
        concept_generation_flow_builder.add_node("concept_enrichment_node", self.create_concept_generation_swarm(state, config))
        
        concept_generation_graph = concept_generation_flow_builder.compile().invoke(state, config)
        
        return concept_generation_graph
    
    def run(self, state: ConceptGenerationState, config: RunnableConfig):
        
        result = self.concept_generation_flow(state, config)
                
        return Command(
            update = {
                "messages": [HumanMessage(content="Proyectos generados exitosamente")],
                "conceptos_enriquecidos": result.conceptos_enriquecidos
            },
            goto="project_selection"
        )

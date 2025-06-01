from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from typing import Literal

from ..state import FormuladorCTeIAgent
from .deep_research.deep_research import DeepResearchEntidades
from .concept_generation.concept_generation import ConceptGenerationFlow

class ProjectStructure:
    def __init__(self):
        self.deep_research_manager = DeepResearchEntidades()
        self.concept_generation_manager = ConceptGenerationFlow()
        # Consider adding a logger here if you have a logging setup
        self.graph = self._build_graph()

    def _build_graph(self):
        project_structure_builder = StateGraph(FormuladorCTeIAgent)
        project_structure_builder.set_entry_point("deep_research_node")
        
        # Pass the methods directly. LangGraph will handle passing state and config.
        project_structure_builder.add_node("deep_research_node", self.deep_research_manager.run)
        project_structure_builder.add_node("concept_generation_node", self.concept_generation_manager.run)

        return project_structure_builder.compile()
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["project_selection"]]:
        final_state_after_subgraph = self.graph.invoke(state, config)
        
        return Command(
            update = {
                "messages": final_state_after_subgraph.get("messages", []) + [HumanMessage(content="Subgrafo de estructura de proyecto completado.")],
                "perfil_entidades": final_state_after_subgraph.get("perfil_entidades"),
                "conceptos_enriquecidos": final_state_after_subgraph.get("conceptos_enriquecidos"),
            },
            goto="project_selection"
        )


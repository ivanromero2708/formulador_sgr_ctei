from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from ..state import FormuladorCTeIAgent
from .deep_research.deep_research import DeepResearchEntidades
from .concept_generation.concept_generation import ConceptGenerationFlow

class ProjectStructure:
    def __init__(self):
        self.deep_research_manager = DeepResearchEntidades()
        self.concept_generation_manager = ConceptGenerationFlow()
        # Consider adding a logger here if you have a logging setup

    def project_structure_graph(self, state: FormuladorCTeIAgent, config: RunnableConfig):
        project_structure_builder = StateGraph(FormuladorCTeIAgent)
        project_structure_builder.set_entry_point("deep_research_node")
        project_structure_builder.add_node("deep_research_node", self.deep_research_manager.run(state, config))
        project_structure_builder.add_node("concept_generation_node", self.concept_generation_manager.run(state, config))
        
        project_structure_graph = project_structure_builder.compile()
        return project_structure_graph
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> FormuladorCTeIAgent:
        
        project_structure_graph = self.project_structure_graph(state, config)
        
        result = project_structure_graph.invoke(state, config)
        
        return Command(
            update = {
                "messages": [HumanMessage(content="Proyectos generados exitosamente")],
                "conceptos_enriquecidos": result.conceptos_enriquecidos
            },
            goto="project_selection"
        )


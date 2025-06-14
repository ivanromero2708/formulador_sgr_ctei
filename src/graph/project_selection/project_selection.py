from src.graph.state import FormuladorCTeIAgent
from langgraph.types import Command, interrupt
from langchain_core.runnables import RunnableConfig
from typing import Literal


class ProjectSelection:
    def __init__(self):
        # Initialization for ProjectSelection node
        pass
    
    def formulator_feedback(self, state: FormuladorCTeIAgent, config: RunnableConfig):
        human_response = interrupt(
            {
                "conceptos_enriquecidos": state.get("conceptos_enriquecidos", []),
                "instructions": (
                    "Por favor seleccione el proyecto deseado y edite los componentes si aplica"
                )
            }
        )
        return Command(
            goto = "project_initiation",
            update = {
                "concepto_seleccionado": human_response,
            }
        )
    
    def run(self, state: FormuladorCTeIAgent,  config: RunnableConfig) -> Command[Literal["project_initiation"]]:
        return self.formulator_feedback(state, config)

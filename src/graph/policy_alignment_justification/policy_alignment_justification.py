
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from typing import Literal
from ..state import FormuladorCTeIAgent
from langchain_core.runnables import RunnableConfig

class PolicyAlignmentJustification:
    def __init__(self):
        pass
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["financial_planning_review"]]:
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Subgrafo de alineación de políticas y justificación completado.")],
            },
            goto="financial_planning_review"
        )
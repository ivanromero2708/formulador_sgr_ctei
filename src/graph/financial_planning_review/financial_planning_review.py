
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from typing import Literal
from ..state import FormuladorCTeIAgent
from langchain_core.runnables import RunnableConfig

class FinancialPlanningReview:
    def __init__(self):
        pass
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["render_documentation"]]:
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Subgrafo de planeación financiera completado.")],
            },
            goto="render_documentation"
        )
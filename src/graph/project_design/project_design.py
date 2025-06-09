from langchain_core.messages import HumanMessage
from langgraph.types import Command
from typing import Literal
from ..state import FormuladorCTeIAgent
from langchain_core.runnables import RunnableConfig

class ProjectDesign:
    def __init__(self) -> None:
        pass
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["policy_alignment_justification"]]:
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Subgrafo de diseño completado.")],
            },
            goto="policy_alignment_justification"
        )
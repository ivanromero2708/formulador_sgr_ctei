from ..state import FormuladorCTeIAgent
from langgraph.types import Command
from typing import Literal

class RenderDocumentation:
    def __init__(self):
        # Initialization for RenderDocumentation node
        pass

    def run(self, state: FormuladorCTeIAgent) -> Command[Literal["__end__"]]:
        return Command(
            goto = "__end__"
        )

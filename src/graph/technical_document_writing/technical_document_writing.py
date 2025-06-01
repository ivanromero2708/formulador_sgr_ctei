from ..state import FormuladorCTeIAgent
from langgraph.types import Command
from typing import Literal

class TechnicalDocumentWriting:
    def __init__(self):
        # Initialization for TechnicalDocumentWriting node
        pass

    def run(self, state: FormuladorCTeIAgent) -> Command[Literal["render_documentation"]]:
        return Command(
            goto = "render_documentation"
        )

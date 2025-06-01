from ..state import FormuladorCTeIAgent
from langgraph.types import Command
from typing import Literal
    
class BudgetCalculation:
    def __init__(self):
        # Initialization for BudgetCalculation node
        pass

    def run(self, state: FormuladorCTeIAgent) -> Command[Literal["technical_document_writing"]]:
        return Command(
            goto = "technical_document_writing"
        )

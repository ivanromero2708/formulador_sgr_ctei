from src.graph.state import FormuladorCTeIAgent
from src.config.configuration import MultiAgentConfiguration
from src.tools import SchemaInputTool
from src.utils.json_utils import repair_json_output
from src.llms.llm import create_llm_model
from src.prompts.template import apply_prompt_template

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent

from typing import Literal

class SchemaEntradaBuilder:
    def __init__(self):
        pass
    
    def create_agent_schema_entrada_builder(self, config: RunnableConfig):
        """Crea un agente con la configuración y el estado proporcionados."""
        
        # Inicialización de la configuración del agente
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt4omini
        
        return create_react_agent(
            create_llm_model(model=agent_model),
            tools=[SchemaInputTool],
            prompt=lambda state: apply_prompt_template("schema_entrada", state),
            name="agente_schema_entrada",  # Asigna explícitamente el nombre del agente aquí
            state_schema = FormuladorCTeIAgent,  # Se pasa la clase, no la instancia
        )
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["coordinador_general"]]:
        """Ejecuta el agente de revisión de entrada estructurada."""
        result = self.create_agent_schema_entrada_builder(config).invoke(state)
        
        response_content = result["messages"][-1].content
        response_content = repair_json_output(response_content)

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=response_content,
                        name="agente_schema_entrada",
                    )
                ]
            },
            goto="coordinador_general",
        )

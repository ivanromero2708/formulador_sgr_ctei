from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from langgraph.types import Command
from langsmith import traceable
from typing import Literal, Any
from src.llms.llm import create_llm_model
from src.prompts.template import apply_prompt_template
from src.tools.local_research_query_tool import local_research_query_tool
from src.config.configuration import MultiAgentConfiguration
from src.utils.json_utils import repair_json_output
from src.graph.state import SeccionTDR

from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

class TDRParsingAgentState(AgentState):
    seccion_tdr: str
    persist_path: str

class TDRParsingAgent:
    def __init__(self):
        pass
    
    def create_tdr_react_agent(self, config: RunnableConfig) -> Any:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        tdr_react_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=[local_research_query_tool],
            prompt=lambda state: apply_prompt_template("tdr_parsing_agent", state),
            name="agente_tdr_parsing",  # Explicitamente asignado
            state_schema=TDRParsingAgentState,  # Se usa nuestro esquema con campos específicos
        )
        return tdr_react_agent_builder
        
    @traceable
    def run(self, state: TDRParsingAgentState, config: RunnableConfig) -> Command[Literal["coordinador_general", "project_structure"]]:
        """
        Parses the TDR document to extract key information and updates the state.
        """
        print("---EJECUTANDO NODO: TDRParsing---")

        try:
            tdr_parsing_agent_graph = self.create_tdr_react_agent(config)
            
            invoke_config = config.copy() if config else {}
            invoke_config["recursion_limit"] = 50
            result = tdr_parsing_agent_graph.invoke(state, invoke_config)
            
            response_content = result["messages"][-1].content
            response_content = repair_json_output(response_content)
            
            return Command(
                update={
                    "secciones_tdr": [SeccionTDR(nombre=state["seccion_tdr"], contenido=response_content)],
                },
                goto="project_structure",
            )
            
        except ValueError as e:
            error_message = f"Error cargando el documento TDR: {str(e)}"
            print(error_message)
            return Command(
                update={
                    "messages": state.get("messages", []) + [AIMessage(content=error_message, name="TDRParsing")],
                },
                goto="coordinador_general",
            )
        
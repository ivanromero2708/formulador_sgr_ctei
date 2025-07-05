from langchain_core.tools import tool
from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import MessagesState
from langgraph.types import Command, Send

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Annotated, Literal, TypedDict
import operator
import json

from src.tools.serper_dev_tool import serper_dev_search_tool
from src.tools.web_rag_pipeline_copy import web_rag_pipeline_tool
from src.config.configuration import MultiAgentConfiguration
from src.llms.llm import create_llm_model
from src.prompts.prompts_project_design import SYSTEM_PROMPT_SUPERVISOR_MARCO_CONCEPTUAL, SYSTEM_PROMPT_RESEARCH_MARCO_CONCEPTUAL 
from src.graph.state import FormuladorCTeIAgent

@tool
class Seccion(BaseModel):
    """Seccion del reporte."""
    nombre: str = Field(
        description="Nombre de esta sección del reporte.",
    )
    descripcion: str = Field(
        description="Alcance de la investigacion de esta seccion del reporte.",
    )
    contenido: str = Field(
        description="El contenido de esta seccion"
    )

@tool
class Secciones(BaseModel):
    """Lista de objetos de seccion del reporte, cada uno con un nombre y descripción detalladas."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    secciones: List[Seccion] = Field(
        description="Una lista de objetos de seccion, cada uno definiendo una parte del reporte a investigar.",
    )

## Estado
class ReportStateOutput(TypedDict):
    reporte_final: str # Final report

class ReportState(FormuladorCTeIAgent):
    secciones: list[Seccion] # List of report sections 
    secciones_completadas: Annotated[list, operator.add] # Send() API key
    reporte_final: str # Final report

class SectionState(MessagesState):
    seccion: str # Report section  
    secciones_completadas: list[Seccion] # Final key we duplicate in outer state for Send() API

class SectionOutputState(TypedDict):
    secciones_completadas: list[Seccion] # Final key we duplicate in outer state for Send() API

## Definicion del Sistema Agentico

class DeepResearchMarcoConceptual:
    def __init__(self):
        self.tools_for_supervisor = [serper_dev_search_tool, web_rag_pipeline_tool, Secciones]
        self.supervisor_tools_by_name = {tool.name: tool for tool in self.tools_for_supervisor}
        self.tools_for_research = [serper_dev_search_tool, web_rag_pipeline_tool, Seccion]
        self.research_tools_by_name = {tool.name: tool for tool in self.tools_for_research}
    
    def supervisor(self, state: ReportState, config: RunnableConfig):
        """LLM decides whether to call a tool or not"""

        # Messages
        messages = state["messages"]

        # Get configuration
        configurable = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = configurable.gpt41mini
        
        # Initialize the model
        llm = create_llm_model(agent_model)
        
        # If sections have been completed, signal to end the process, skipping introduction and conclusion.
        if state.get("secciones_completadas") and not state.get("reporte_final"):
            completion_message_content = (
                "Todo el cuerpo de las secciones han sido completado."
                "El proceso concluira, saltando la generacion de las secciones de introduccion y conclusion."
            )
            final_ai_message = AIMessage(content=completion_message_content)
            return {
                "messages": messages + [final_ai_message], 
                "reporte_final": "\n\n".join(
                    [
                        sec.contenido for sec in state["secciones_completadas"]
                    ]
                )
            }

        # Get tools based on configuration
        supervisor_tool_list = self.tools_for_supervisor
        
        # Invoke
        return {
            "messages": [
                llm.bind_tools(supervisor_tool_list, parallel_tool_calls=False).invoke(
                    [
                        {"role": "system",
                        "content": SYSTEM_PROMPT_SUPERVISOR_MARCO_CONCEPTUAL,
                        }
                    ]
                    + messages
                )
            ]
        }
    
    def supervisor_tools(self, state: ReportState, config: RunnableConfig)  -> Command[Literal["supervisor", "research_team", "__end__"]]:
        """Performs the tool call and sends to the research agent"""

        result = []
        sections_list = []

        # Get tools based on configuration
        supervisor_tools_by_name = self.supervisor_tools_by_name
        
        # First process all tool calls to ensure we respond to each one (required for OpenAI)
        for tool_call in state["messages"][-1].tool_calls:
            # Get the tool
            tool = supervisor_tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            content_for_message = ""

            if isinstance(observation, str):
                content_for_message = observation
            elif isinstance(observation, BaseModel):
                content_for_message = observation # LangChain handles Pydantic model serialization
            elif isinstance(observation, list):
                try:
                    content_for_message = json.dumps(observation)
                except TypeError:
                    content_for_message = str(observation) # Fallback for non-serializable list content
            elif isinstance(observation, dict):
                try:
                    content_for_message = json.dumps(observation)
                except TypeError:
                    content_for_message = str(observation) # Fallback for non-serializable dict
            else:
                content_for_message = str(observation) # Fallback for other types

            # Append to messages 
            result.append({"role": "tool", 
                        "content": content_for_message, 
                        "name": tool_call["name"], 
                        "tool_call_id": tool_call["id"]})
            
            # Store special tool results for processing after all tools have been called
            if tool_call["name"] == "Secciones":
                sections_list = observation.secciones
        
        # After processing all tool calls, decide what to do next
        if sections_list:
            # Send the sections to the research agents
            return Command(goto=[Send("research_team", {"seccion": s}) for s in sections_list], update={"messages": result})
        
        # Default case (for search tools, etc.)
        total_sections = len(state.get("secciones", []))
        done_sections  = len(state.get("secciones_completadas", []))

        if done_sections >= total_sections and total_sections > 0:
            # Ensamblamos el cuerpo del reporte
            body = "\n\n".join([sec.contenido for sec in state["secciones_completadas"]])
            # Actualizamos y forzamos el END del flujo
            return Command(
                goto=END,
                update={
                    "reporte_final": body,
                    "messages": result + [
                        {"role": "assistant", "content": "He generado todas las secciones. Reporte completo."}
                    ]
                }
            )
        return Command(goto="supervisor", update={"messages": result})
    
    def supervisor_should_continue(self, state: ReportState) -> Literal["supervisor_tools", END]:
        """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM makes a tool call, then perform an action
        if last_message.tool_calls:
            return "supervisor_tools"
        
        # Else end because the supervisor asked a question or is finished
        else:
            return END
    
    def research_agent(self, state: SectionState, config: RunnableConfig):
        """LLM decides whether to call a tool or not"""
        
        # Get configuration
        configurable = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = configurable.gpt41mini
        
        # Initialize the model
        llm = create_llm_model(agent_model)

        # Get tools based on configuration
        research_tool_list = self.tools_for_research
        
        return {
            "messages": [
                # Enforce tool calling to either perform more search or call the Section tool to write the section
                llm.bind_tools(research_tool_list).invoke(
                    [
                        {"role": "system",
                        "content": SYSTEM_PROMPT_RESEARCH_MARCO_CONCEPTUAL.format(nombre_seccion= state["seccion"]["nombre"], descripcion_seccion=state["seccion"]["descripcion"])
                        }
                    ]
                    + state["messages"]
                )
            ]
        }
    
    def research_agent_tools(self, state: SectionState, config: RunnableConfig):
        """Performs the tool call and route to supervisor or continue the research loop"""

        result = []
        completed_section = None
        
        # Get tools based on configuration
        research_tools_by_name = self.research_tools_by_name
        
        # Process all tool calls first (required for OpenAI)
        for tool_call in state["messages"][-1].tool_calls:
            # Get the tool
            tool = research_tools_by_name[tool_call["name"]]
            # Perform the tool call 
            observation = tool.invoke(tool_call["args"])
            content_for_message = ""

            if isinstance(observation, str):
                content_for_message = observation
            elif isinstance(observation, BaseModel):
                content_for_message = observation # LangChain handles Pydantic model serialization
            elif isinstance(observation, list):
                try:
                    content_for_message = json.dumps(observation)
                except TypeError:
                    content_for_message = str(observation) # Fallback for non-serializable list content
            elif isinstance(observation, dict):
                try:
                    content_for_message = json.dumps(observation)
                except TypeError:
                    content_for_message = str(observation) # Fallback for non-serializable dict
            else:
                content_for_message = str(observation) # Fallback for other types

            # Append to messages
            result.append({"role": "tool", 
                        "content": content_for_message, 
                        "name": tool_call["name"], 
                        "tool_call_id": tool_call["id"]})
            
            # Store the section observation if a Section tool was called
            if tool_call["name"] == "Seccion":
                completed_section = observation
        
        # After processing all tools, decide what to do next
        if completed_section:
            # Write the completed section to state and return to the supervisor
            return {"messages": result, "secciones_completadas": [completed_section]}
        else:
            # Continue the research loop for search tools, etc.
            return {"messages": result}
    
    def research_agent_should_continue(self, state: SectionState) -> Literal["research_agent_tools", END]:
        """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

        messages = state["messages"]
        last_message = messages[-1]

        # If the LLM makes a tool call, then perform an action
        if last_message.tool_calls:
            return "research_agent_tools"

        else:
            return END
    
    def build_graph(self):
        # Research agent workflow
        research_builder = StateGraph(SectionState, output=SectionOutputState, config_schema=MultiAgentConfiguration)
        research_builder.add_node("research_agent", self.research_agent)
        research_builder.add_node("research_agent_tools", self.research_agent_tools)
        research_builder.add_edge(START, "research_agent") 
        research_builder.add_conditional_edges(
            "research_agent",
            self.research_agent_should_continue,
            {
                # Name returned by should_continue : Name of next node to visit
                "research_agent_tools": "research_agent_tools",
                END: END,
            },
        )
        research_builder.add_edge("research_agent_tools", "research_agent")

        # Supervisor workflow
        supervisor_builder = StateGraph(ReportState, input=MessagesState, output=ReportStateOutput, config_schema=MultiAgentConfiguration)
        supervisor_builder.add_node("supervisor", self.supervisor)
        supervisor_builder.add_node("supervisor_tools", self.supervisor_tools)
        supervisor_builder.add_node("research_team", research_builder.compile())

        # Flow of the supervisor agent
        supervisor_builder.add_edge(START, "supervisor")
        supervisor_builder.add_conditional_edges(
            "supervisor",
            self.supervisor_should_continue,
            {
                # Name returned by should_continue : Name of next node to visit
                "supervisor_tools": "supervisor_tools",
                END: END,
            },
        )
        supervisor_builder.add_edge("research_team", "supervisor")

        return supervisor_builder.compile()
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["desarrollo_cadena_valor"]]:
        print("--- Ejecutando Nodo: Desarrollo del Marco Conceptual ---")
        antecedentes = state.get("antecedentes", "")
        problema_central = state.get("problema_central", "")
        descripcion_problema = state.get("descripcion_problema", "")
        magnitud_problema = state.get("magnitud_problema", "")        
        poblacion_afectada = state.get("poblacion_afectada")
        poblacion_objetivo = state.get("poblacion_objetivo")
        objetivos_especificos = state.get("objetivos_especificos")
        
        prompt = f"""Investiga de manera profunda los aspectos conceptuales que enmarcand el problema, necesidad u oportunidad abordado por el proyecto, inclkuyendo el Marco de Política Pública, Marco Normativo según aplique en Colombia. Haz esto en 4 secciones.
            Antecedentes del proyecto:\n{antecedentes}
            Problema central:\n{problema_central}
            Descripción del problema:\n{descripcion_problema}
            Magnitud del problema:\n{magnitud_problema}
            Población afectada:\n{poblacion_afectada}
            Población objetivo:\n{poblacion_objetivo}
            Objetivos específicos:\n{objetivos_especificos}
            Por favor, busca información relevante y actualizada."""
        
        msg = HumanMessage(
            content = prompt
        )
        
        invoke_config = config.copy() if config else {}
        invoke_config["recursion_limit"] = 100
        
        response = self.build_graph().invoke({"messages": [msg]}, invoke_config)
        
        goto = [
            Send(
                "desarrollo_cadena_valor",
                {
                    "objetivo_general": state.get("objetivo_general"),
                    "objetivo_especifico": objetivo_especifico
                }                    
            )
            for objetivo_especifico in state.get("objetivos_especificos", [])
        ]
        
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Diseño del proyecto terminado")],
                "marco_conceptual": response.get("reporte_final")
            },
            goto=goto
        )
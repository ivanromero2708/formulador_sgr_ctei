import warnings
# Suprimir warning de Pydantic sobre StructuredTool args_schema
warnings.filterwarnings(
    "ignore",
    message=r".*StructuredTool.*is not a Python type.*",
    category=UserWarning
)

from langchain_core.messages import AIMessage
from langgraph.graph import START, END, StateGraph
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import Command, Send
from langgraph.graph import MessagesState

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Annotated, Literal, TypedDict
import operator
import json

from src.graph.state import FormuladorCTeIAgent
from src.config.configuration import MultiAgentConfiguration
from src.llms.llm import create_llm_model
from src.tools.serper_dev_tool import serper_dev_search_tool
from src.tools.web_rag_pipeline import web_rag_pipeline_tool
from src.prompts.prompts_project_initiation import SUPERVISOR_INSTRUCTIONS, RESEARCH_INSTRUCTIONS
from typing import Any, Dict, List, Union
from pydantic import BaseModel

def build_prompt(
    title: str,
    sections: Dict[str, Union[BaseModel, Dict[str, Any], List[Any], str]],
    labels: Dict[str, str],
    footer_lines: List[str] = None
) -> str:
    """
    title: línea inicial del prompt.
    sections: dict donde:
      - clave = nombre de sección (p.ej. 'alianzas_usuario')
      - valor = BaseModel | dict de campo->valor | lista de items | string
    labels: map de campo o sección -> etiqueta de impresión.
    footer_lines: líneas finales que siempre quieras añadir.
    """
    lines = [title.rstrip()]

    for section_name, fields in sections.items():
        etiqueta_seccion = labels.get(section_name, section_name.replace("_", " ").capitalize())

        # 1) Si es None o vacío:
        if not fields and fields != 0:
            lines.append(f"- {etiqueta_seccion}: No disponible.")
            continue

        # 2) Si es lista, imprimimos viñetas directamente:
        if isinstance(fields, list):
            if fields:
                bullet_list = "\n  • ".join(str(item) for item in fields)
                lines.append(f"- {etiqueta_seccion}:\n  • {bullet_list}")
            else:
                lines.append(f"- {etiqueta_seccion}: No especificados.")
            continue

        # 3) Si es string (o cualquier otro tipo escalar), lo imprimimos en la misma línea:
        if isinstance(fields, (str, int, float)):
            lines.append(f"- {etiqueta_seccion}: {fields}")
            continue

        # 4) Si es un BaseModel, volcamos a dict; si es dict, lo usamos tal cual
        if isinstance(fields, BaseModel):
            data = fields.model_dump()
        else:
            data = fields  # asumimos que es dict

        # 5) Recorremos cada par campo->valor dentro de la sección
        for field, raw in data.items():
            etiqueta = labels.get(field, field.replace("_", " ").capitalize())
            if isinstance(raw, list):
                if raw:
                    bullet_list = "\n  • ".join(str(item) for item in raw)
                    lines.append(f"- {etiqueta}:\n  • {bullet_list}")
                else:
                    lines.append(f"- {etiqueta}: No especificados.")
            else:
                valor = raw or "No especificado"
                lines.append(f"- {etiqueta}: {valor}")

    # Añadimos líneas finales si las hay
    if footer_lines:
        lines.append("")  # salto de línea antes del footer
        lines.extend(footer_lines)

    return "\n".join(lines)


@tool
class Section(BaseModel):
    """Section of the report."""
    name: str = Field(
        description="Name for this section of the report.",
    )
    description: str = Field(
        description="Research scope for this section of the report.",
    )
    content: str = Field(
        description="The content of the section."
    )

@tool
class Sections(BaseModel):
    """List of section objects for the report, each with a name and a detailed description."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    sections: List[Section] = Field(
        description="A list of Section objects, each defining a part of the report to be researched.",
    )

## State
class ReportStateOutput(TypedDict):
    final_report: str # Final report

class ReportState(FormuladorCTeIAgent):
    sections: list[Section] # List of report sections 
    completed_sections: Annotated[list, operator.add] # Send() API key
    final_report: str # Final report

class SectionState(MessagesState):
    section: str # Report section  
    completed_sections: list[Section] # Final key we duplicate in outer state for Send() API

class SectionOutputState(TypedDict):
    completed_sections: list[Section] # Final key we duplicate in outer state for Send() API



class DeepResearchAntecedentes:
    def __init__(self):
        self.tools_for_supervisor = [serper_dev_search_tool, web_rag_pipeline_tool, Sections]
        self.supervisor_tools_by_name = {tool.name: tool for tool in self.tools_for_supervisor}
        self.tools_for_research = [serper_dev_search_tool, web_rag_pipeline_tool, Section]
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
        if state.get("completed_sections") and not state.get("final_report"):
            completion_message_content = (
                "All main body sections have been completed. "
                "The process will now conclude, skipping the generation of introduction and conclusion sections."
            )
            final_ai_message = AIMessage(content=completion_message_content)
            return {"messages": messages + [final_ai_message], "final_report": "\n\n".join([sec.content for sec in state["completed_sections"]])}

        # Get tools based on configuration
        supervisor_tool_list = self.tools_for_supervisor
        
        # Invoke
        return {
            "messages": [
                llm.bind_tools(supervisor_tool_list, parallel_tool_calls=False).invoke(
                    [
                        {"role": "system",
                        "content": SUPERVISOR_INSTRUCTIONS,
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
            if tool_call["name"] == "Sections":
                sections_list = observation.sections
        
        # After processing all tool calls, decide what to do next
        if sections_list:
            # Send the sections to the research agents
            return Command(goto=[Send("research_team", {"section": s}) for s in sections_list], update={"messages": result})
        
        # Default case (for search tools, etc.)
        total_sections = len(state.get("sections", []))
        done_sections  = len(state.get("completed_sections", []))

        if done_sections >= total_sections and total_sections > 0:
            # Ensamblamos el cuerpo del reporte
            body = "\n\n".join([sec.content for sec in state["completed_sections"]])
            # Actualizamos y forzamos el END del flujo
            return Command(
                goto=END,
                update={
                    "final_report": body,
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
                llm.bind_tools(research_tool_list, parallel_tool_calls=True).invoke(
                    [
                        {"role": "system",
                        "content": RESEARCH_INSTRUCTIONS.format(nombre_seccion= state["section"]["name"], descripcion_seccion=state["section"]["description"])
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
            if tool_call["name"] == "Section":
                completed_section = observation
        
        # After processing all tools, decide what to do next
        if completed_section:
            # Write the completed section to state and return to the supervisor
            return {"messages": result, "completed_sections": [completed_section]}
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
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["loading_research_groups_info"]]:
        concepto = state.get("concepto_seleccionado")
        entidad = state.get("entidad_proponente_usuario")
        alianzas = state.get("alianzas_usuario")
        depto = state.get("departamento")

        # definimos etiquetas amigables para cada campo
        etiquetas = {
            "titulo_sugerido": "Concepto del Proyecto",
            "objetivo_general": "Objetivo General",
            "problema_abordado": "Problema Abordado",
            "objetivos_especificos": "Objetivos Específicos",
            "resultados_esperados": "Resultados Esperados",
            "nombre": "Entidad Proponente",
            "alianzas_usuario": "Entidades Aliadas",
            "departamento": "Departamento de Enfoque",
        }

        # construimos el prompt
        prompt = build_prompt(
            title="Investiga los antecedentes para un proyecto con las siguientes características:",
            sections={
                "concepto_proyecto": concepto,
                "entidad_proponente_usuario": {"nombre": entidad and entidad.nombre} if entidad else {},
                "alianzas_usuario": [a.nombre for a in alianzas] if alianzas else [],
                "departamento": depto,
            },
            labels=etiquetas,
            footer_lines=[
                "Por favor, busca antecedentes relevantes a nivel internacional, nacional y departamental.",
                "Identifica desarrollos previos, resultados, lecciones aprendidas y cómo se relacionan con el contexto regional y departamental."
            ]
        )

        user_message_content = prompt
        msg = [{"role": "user", "content": user_message_content}]
        
        invoke_config = config.copy() if config else {}
        invoke_config["recursion_limit"] = 100
        
        response = self.build_graph().invoke({"messages": msg}, invoke_config)

        print(response)
        
        return Command(
            update={"antecedentes": response.get("final_report")},
            goto="loading_research_groups_info"
        )
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import StateGraph
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from langchain_core.messages import AIMessage

from typing import Literal, List
from pydantic import Field
from trustcall import create_extractor

from src.graph.state import FormuladorCTeIAgent, IdentificacionProyecto, GrupoInvestigacionProyecto
from src.graph.project_initiation.deep_research_antecedentes.deep_research_antecedentes import DeepResearchAntecedentes
from src.config.configuration import MultiAgentConfiguration
from src.llms.llm import create_llm_model
from src.prompts.template import apply_prompt_template, get_prompt_template


class ProjectInitiationState(FormuladorCTeIAgent):
    identificacion_proyecto: IdentificacionProyecto = Field(default=None, description="Identificación del proyecto")
    palabras_clave: str = Field(default=None, description="Palabras clave del proyecto")
    antecedentes: str = Field(..., description="Antecedentes identificados en relación con la problemática, necesidad u oportunidad a abordar en el marco del proyecto. Adicionalmente, presentar el desarrollo previo de iniciativas a nivel internacional, nacional, departamental o municipal en el marco de la temática del proyecto; así como los resultados de éstas, que ilustran la pertinencia de desarrollar el proyecto que se presenta. Nota: En lo posible relacione la información anterior con el contexto regional y departamental.")
    idoneidad_trayectoria_proponentes: str = Field(..., description = "Descripción de los aportes de los integrantes de la alianza para la contribución a la consecución de los objetivos y actividades del proyecto. Los aportes de los integrantes de la alianza deben ser individuales y contemplar al menos uno o más de uno de los siguientes aportes: financieros, técnicos /tecnológicos y de talento humano de alto nivel. Esto debe guardar total coherencia con la información suministrada en la Carta aval, compromiso institucional y modelo de gobernanza y en el presupuesto del proyecto.")
    grupos_investigacion_proyecto: List[GrupoInvestigacionProyecto] = Field(default=None, description="Grupos de investigación vinculados al proyecto")

class ProjectInitiation:
    def __init__(self):
        self.deep_research_antecedentes = DeepResearchAntecedentes()
    
    def project_identification(self, state: ProjectInitiationState, config: RunnableConfig) -> Command[Literal["project_research"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_config_name = agent_configuration.o4mini

        # Obtener la instancia del LLM
        llm_instance = create_llm_model(llm_config_name)

        # Crear el extractor de trustcall
        extractor = create_extractor(
            llm_instance,
            tools=[IdentificacionProyecto],
            tool_choice=IdentificacionProyecto.__name__
        )
        
        input_messages = apply_prompt_template("project_identification", state)
        
        trustcall_input = {"messages": input_messages}
        extraction_result = extractor.invoke(trustcall_input)
        
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content="",
                        name="project_identification",
                    )
                ],
                "identificacion_proyecto": extraction_result["responses"][0],
            },
            goto="project_research"
        )
    
    def loading_research_groups_info(self, state: ProjectInitiationState, config: RunnableConfig) -> Command[Literal["project_member_analysis"]]:
        human_response = interrupt(
            {
                "grupos_investigacion_proyecto": state.get("grupos_investigacion_proyecto", []),
                "instructions": (
                    "Por favor indique los grupos de investigación que participarán en el proyecto."
                )
            }
        )        
        return Command(
            goto = "project_member_analysis",
            update = {
                "grupos_investigacion_proyecto": human_response["grupos_investigacion_proyecto"],
            }
        )
    
    def project_member_analysis(self, state: ProjectInitiationState, config: RunnableConfig) -> Command[Literal["__end__"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_config_name = agent_configuration.o4mini

        # Obtener la instancia del LLM
        llm_instance = create_llm_model(llm_config_name)
        
        input_messages = apply_prompt_template("project_member_analysis", state)

        llm_instance_input = {"messages": input_messages}
        
        project_member_analysis_result = llm_instance.invoke(input_messages)
        
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content="",
                        name="project_member_analysis",
                    )
                ],
                "idoneidad_trayectoria_proponentes": project_member_analysis_result.content,
            },
            goto="__end__"
        )
    
    def build_graph(self):
        builder = StateGraph(ProjectInitiationState)
        builder.set_entry_point("project_identification")
        builder.add_node("project_identification", self.project_identification)
        builder.add_node("project_research", self.deep_research_antecedentes.run)
        builder.add_node("loading_research_groups_info", self.loading_research_groups_info)
        builder.add_node("project_member_analysis", self.project_member_analysis)
        return builder.compile()
    
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["analytical_core"]]:
        
        invoke_config = config.copy() if config else {}
        invoke_config["recursion_limit"] = 100
        
        results_project_initiation = self.build_graph().invoke(state, invoke_config)
        
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Subgrafo de iniciación del proyecto completado.")],
                "identificacion_proyecto": results_project_initiation.get("identificacion_proyecto", ""),
                "palabras_clave": results_project_initiation.get("palabras_clave", ""),
                "antecedentes": results_project_initiation.get("antecedentes", ""),
                "idoneidad_trayectoria_proponentes": results_project_initiation.get("idoneidad_trayectoria_proponentes", ""),
                "grupos_investigacion_proyecto": results_project_initiation.get("grupos_investigacion_proyecto", ""),
            },
            goto="analytical_core"
        )
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph

from typing import Literal
from pydantic import BaseModel, Field
from typing import List

from src.graph.state import (
    FormuladorCTeIAgent, 
    ProblemTreeState, 
    Participante,
    PoblacionAfectada,
    PoblacionObjetivo,
    EnfoqueDiferencial,
    ObjetivoGeneral,
    Indicador,
    ArbolDeObjetivos,
    Alternativa,
)
from src.config.configuration import MultiAgentConfiguration
from src.llms.llm import create_llm_model
from src.prompts.template import apply_prompt_template
from src.tools.local_research_query_tool import local_research_query_tool

class ProblemaIdentificacionOutput(BaseModel):
    problema_central: str
    descripcion_problema: str
    magnitud_problema: str
    arbol_problema: ProblemTreeState

class AnalisisParticipantesOutput(BaseModel):
    participantes: List[Participante] = Field(..., description="Lista completa de las entidades analizadas.")

class AnalisisPoblacion(BaseModel):
    """
    Modelo de datos principal y completo para la sección '11. POBLACIÓN'.
    """
    poblacion_afectada: PoblacionAfectada = Field(..., description="Detalles de la sección 11.1.")
    poblacion_objetivo: PoblacionObjetivo = Field(..., description="Detalles de la sección 11.2.")
    
    caracteristicas_demograficas_objetivo: str = Field(
        ...,
        description="Texto que caracteriza a las personas que conforman la población objetivo y su perfil."
    )
    enfoque_diferencial: EnfoqueDiferencial = Field(
        ...,
        description="Análisis detallado del enfoque diferencial del proyecto, según el apartado 11.3."
    )
    cumple_porcentaje_vinculacion_diferencial: bool = Field(
        ...,
        description="Responde a la pregunta del apartado 11.4: ¿Más del 50% pertenece a una categoría o más del 41% a dos o más?"
    )

    @model_validator(mode='after')
    def validar_consistencia_poblaciones(self):
        """
        Asegura que la población objetivo no sea mayor que la población afectada.
        """
        if self.poblacion_objetivo.cantidad > self.poblacion_afectada.cantidad:
            raise ValueError("La cantidad de la población objetivo no puede ser mayor a la de la población afectada.")
        return self

class AnalisisDeObjetivos(BaseModel):
    """
    Modelo de datos principal y completo para la sección '12. OBJETIVOS'.
    Este modelo asegura la coherencia lógica entre todas sus partes.
    """
    objetivo_general: ObjetivoGeneral = Field(..., description="Sección 12.1 detallada.")
    objetivos_especificos: List[str] = Field(
        ...,
        min_length=1,
        description="Lista de enunciados de los objetivos específicos (Sección 12.2)."
    )
    arbol_de_objetivos: ArbolDeObjetivos = Field(..., description="Estructura completa del árbol de objetivos (Sección 12.3).")

    @model_validator(mode='after')
    def validar_consistencia_entre_secciones(self):
        """
        Valida que los objetivos definidos en las secciones 12.1 y 12.2
        sean los mismos que se referencian en el árbol de objetivos (12.3).
        """
        # Validar consistencia del Objetivo General
        if self.objetivo_general.enunciado != self.arbol_de_objetivos.objetivo_general_enunciado:
            raise ValueError("El enunciado del objetivo general en la sección 12.1 no coincide con el del árbol de objetivos.")

        # Validar consistencia de los Objetivos Específicos
        # Se convierten a 'set' para ignorar el orden y solo verificar que contengan los mismos elementos.
        set_objetivos_especificos = set(self.objetivos_especificos)
        set_objetivos_arbol = set(self.arbol_de_objetivos.objetivos_especificos_enunciados)

        if set_objetivos_especificos != set_objetivos_arbol:
            raise ValueError("La lista de objetivos específicos en la sección 12.2 no coincide con la del árbol de objetivos.")
        
        return self

class AnalisisDeAlternativas(BaseModel):
    """
    Modelo de datos principal para la sección '14. ANÁLISIS DE LAS ALTERNATIVAS'.
    Este modelo valida las reglas de negocio clave de la metodología.
    """
    alternativas: List[Alternativa] = Field(
        ...,
        min_length=2,
        description="Lista de las alternativas identificadas (se requiere un mínimo de 2)."
    )
    analisis_tecnico_seleccionada: str = Field(
        ...,
        min_length=50,
        description="Análisis detallado (técnico, financiero, etc.) que justifica la selección de una alternativa y el descarte de las demás."
    )

    @model_validator(mode='after')
    def validar_una_sola_alternativa_seleccionada(self):
        """
        Valida dos reglas de negocio cruciales:
        1. Que exactamente UNA de las alternativas esté marcada como seleccionada.
        2. Que la justificación de la alternativa seleccionada explique por qué se eligió,
           y la de las no seleccionadas explique por qué se descartaron.
        """
        seleccionadas = [alt for alt in self.alternativas if alt.es_seleccionada]
        
        if len(seleccionadas) != 1:
            raise ValueError(f"Se debe seleccionar exactamente UNA alternativa. Actualmente hay {len(seleccionadas)} seleccionada(s).")
        
        # Opcional: Validaciones de contenido en la justificación
        for alt in self.alternativas:
            if alt.es_seleccionada and "seleccion" not in alt.justificacion.lower():
                # Advertencia simple, podría ser un error si se desea más estricto
                # print(f"Advertencia: La justificación de la alternativa seleccionada '{alt.nombre}' debería explicar su selección.")
                pass
            if not alt.es_seleccionada and "descarta" not in alt.justificacion.lower():
                # print(f"Advertencia: La justificación de la alternativa no seleccionada '{alt.nombre}' debería explicar su descarte.")
                pass

        return self

class AnalyticalCoreState(FormuladorCTeIAgent):
    problema_central: str
    descripcion_problema: str
    magnitud_problema: str
    arbol_problema: ProblemTreeState
    participantes: List[Participante]
    poblacion_afectada: PoblacionAfectada = Field(..., description="Detalles de la sección 11.1.")
    poblacion_objetivo: PoblacionObjetivo = Field(..., description="Detalles de la sección 11.2.")
    caracteristicas_demograficas_objetivo: str = Field(..., description="Texto que caracteriza a las personas que conforman la población objetivo y su perfil.")
    enfoque_diferencial: EnfoqueDiferencial = Field(..., description="Análisis detallado del enfoque diferencial del proyecto, según el apartado 11.3.")
    cumple_porcentaje_vinculacion_diferencial: bool = Field(..., description="Responde a la pregunta del apartado 11.4: ¿Más del 50% pertenece a una categoría o más del 41% a dos o más?")
    objetivo_general: ObjetivoGeneral = Field(..., description="Sección 12.1 detallada.")
    objetivos_especificos: List[str] = Field(..., min_length=1, description="Lista de enunciados de los objetivos específicos (Sección 12.2).")
    arbol_de_objetivos: ArbolDeObjetivos = Field(..., description="Estructura completa del árbol de objetivos (Sección 12.3).")
    alternativas: List[Alternativa] = Field(..., min_length=2, description="Lista de las alternativas identificadas (se requiere un mínimo de 2).")
    analisis_tecnico_seleccionada: str = Field(..., min_length=50, description="Análisis detallado (técnico, financiero, etc.) que justifica la selección de una alternativa y el descarte de las demás.")
    

class AnalyticalCore:
    def __init__(self) -> None:
        self.tools_problem_identification_agent = [local_research_query_tool]
        self.tools_stakeholder_analysis_agent = []
        self.tools_population_analysis_agent = []
        self.tools_objective_analysis_agent = []
        self.tools_alternative_analysis_agent = []
    
    def problem_identification(self, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        problem_identification_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_problem_identification_agent,
            prompt=lambda state: apply_prompt_template("problem_identification_agent", state),
            response_format=ProblemaIdentificacionOutput,
            name="problem_identification_agent",
            state_schema=AnalyticalCoreState,
        )
        return problem_identification_agent_builder
    
    def stakeholder_analysis(self, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        stakeholder_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=[local_research_query_tool],
            prompt=lambda state: apply_prompt_template("stakeholder_analysis_agent", state),
            response_format=AnalisisParticipantesOutput,
            name="stakeholder_analysis_agent",
            state_schema=AnalyticalCoreState,
        )
        return stakeholder_analysis_agent_builder
    
    def population_analysis(self, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        population_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_population_analysis_agent,
            prompt=lambda state: apply_prompt_template("population_analysis_agent", state),
            response_format=AnalisisPoblacion,
            name="population_analysis_agent",
            state_schema=AnalyticalCoreState,
        )
        return population_analysis_agent_builder
    
    def objective_analysis(self, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        objective_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_objective_analysis_agent,
            prompt=lambda state: apply_prompt_template("objective_analysis_agent", state),
            response_format=AnalisisDeObjetivos,
            name="objective_analysis_agent",
            state_schema=AnalyticalCoreState,
        )
        return objective_analysis_agent_builder
    
    def alternative_analysis(self, config: RunnableConfig):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        alternative_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_alternative_analysis_agent,
            prompt=lambda state: apply_prompt_template("alternative_analysis_agent", state),
            response_format=AnalisisDeAlternativas,
            name="alternative_analysis_agent",
            state_schema=AnalyticalCoreState,
        )
        return alternative_analysis_agent_builder
    
    def build_graph(self):
        builder = StateGraph(AnalyticalCoreState)
        builder.set_entry_point("problem_identification")
        builder.add_node("problem_identification", self.problem_identification)
        builder.add_node("stakeholder_analysis", self.stakeholder_analysis)
        builder.add_node("population_analysis", self.population_analysis)
        builder.add_node("objective_analysis", self.objective_analysis)
        builder.add_node("alternative_analysis", self.alternative_analysis)
        return builder.compile()
    
    def run(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["project_design"]]:
        graph = self.build_graph()
        
        invoke_config = config.copy() if config else {}
        invoke_config["recursion_limit"] = 100
        
        result = graph.invoke(state, invoke_config)
        
        return Command(
            update = {
                "messages": state.get("messages", []) + [HumanMessage(content="Subgrafo de análisis completado.")],
                "problema_central": result.get("problema_central"),
                "descripcion_problema": result.get("descripcion_problema"),
                "magnitud_problema": result.get("magnitud_problema"),
                "arbol_problema": result.get("arbol_problema"),
                "participantes": result.get("participantes"),
                "poblacion_afectada": result.get("poblacion_afectada"),
                "poblacion_objetivo": result.get("poblacion_objetivo"),
                "caracteristicas_demograficas_objetivo": result.get("caracteristicas_demograficas_objetivo"),
                "enfoque_diferencial": result.get("enfoque_diferencial"),
                "cumple_porcentaje_vinculacion_diferencial": result.get("cumple_porcentaje_vinculacion_diferencial"),
                "objetivo_general": result.get("objetivo_general"),
                "objetivos_especificos": result.get("objetivos_especificos"),
                "arbol_de_objetivos": result.get("arbol_de_objetivos"),
                "alternativas": result.get("alternativas"),
                "analisis_tecnico_seleccionada": result.get("analisis_tecnico_seleccionada"),
            },
            goto="project_design"
        )
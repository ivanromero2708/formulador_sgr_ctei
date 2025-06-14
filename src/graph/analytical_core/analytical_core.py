from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph
from langgraph.types import Command

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from typing import List
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SKLearnVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
import os
import uuid

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
from src.tools.serper_dev_tool import serper_dev_search_tool
from src.tools.web_rag_pipeline import web_rag_pipeline_tool

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
    plan_desarrollo_nacional_vectorstore: str
    plan_desarrollo_departamental_vectorstore: str
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
        self.tools_problem_identification_agent = [serper_dev_search_tool, web_rag_pipeline_tool, local_research_query_tool]
        self.tools_stakeholder_analysis_agent = [local_research_query_tool]
        self.tools_population_analysis_agent = [serper_dev_search_tool, web_rag_pipeline_tool, local_research_query_tool]
        self.tools_objective_analysis_agent = []
        self.tools_alternative_analysis_agent = []

    def load_document(self, file_path: str) -> List[Document]:
        """Loads document content from the given file path."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path=file_path)
        elif ext == ".docx":
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Please provide a PDF or DOCX file.")
        
        docs = loader.load()
        if not docs:
            raise ValueError(f"No content could be extracted from {file_path}")
        
        return docs

    def split_documents(self, docs):
        """
        Divide el texto en chunks para crear embeddings.
        :param docs: Documentos (chunks).
        :return: Lista de documentos (chunks).
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        return splitter.split_documents(docs)

    def create_vectorstore(self, splits):
        """
        Crea y persiste un vector store a partir de los chunks de la transcripción.
        :param splits: Lista de chunks.
        :return: vectorstore y la ruta de persistencia.
        """
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Generate a unique filename using UUID
        unique_filename = f"vectorstore_{uuid.uuid4()}.parquet"
        # Usar Path para generar el directorio y convertirlo a POSIX (con "/" como separador)
        persist_path = Path(os.getcwd()) / "temp_uploads" / unique_filename
        
        # Ensure the temp_uploads directory exists
        persist_path.parent.mkdir(parents=True, exist_ok=True)
        
        persist_path_str = persist_path.as_posix()  # Se convierte a formato POSIX ("/")

        vectorstore = SKLearnVectorStore.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_path=persist_path_str, # Use the string version of the path
            serializer="parquet",
        )

        vectorstore.persist()
        return vectorstore, persist_path_str
    
    def RAG_pipeline(self, file_path):
        documents = self.load_document(file_path)
        splits = self.split_documents(documents)
        _, persist_path = self.create_vectorstore(splits)
        return persist_path
        
    def plan_desarrollo_vectorstore(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["problem_identification"]]:
        plan_desarrollo_nacional = state.get("plan_desarrollo_nacional")
        persist_path_plan_desarrollo_nacional = self.RAG_pipeline(plan_desarrollo_nacional)
        
        plan_desarrollo_departamental = state.get("plan_desarrollo_departamental")
        persist_path_plan_desarrollo_departamental = self.RAG_pipeline(plan_desarrollo_departamental)
        
        return Command(
            update={
                "plan_desarrollo_nacional_vectorstore": persist_path_plan_desarrollo_nacional,
                "plan_desarrollo_departamental_vectorstore": persist_path_plan_desarrollo_departamental,
            },
            goto="problem_identification"
        )
    
    def problem_identification(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["stakeholder_analysis"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        problem_identification_agent_graph = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_problem_identification_agent,
            prompt=lambda state: apply_prompt_template("problem_identification_agent", state),
            response_format=ProblemaIdentificacionOutput,
            name="problem_identification_agent",
        )
        
        result = problem_identification_agent_graph.invoke(state, config)
        
        return Command(
            update={
                "problema_central": result.get("structured_response").problema_central,
                "descripcion_problema": result.get("structured_response").descripcion_problema,
                "magnitud_problema": result.get("structured_response").magnitud_problema,
                "arbol_problema": result.get("structured_response").arbol_problema,
            },
            goto="stakeholder_analysis"
        )
    
    def stakeholder_analysis(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["population_analysis"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        stakeholder_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=[local_research_query_tool],
            prompt=lambda state: apply_prompt_template("stakeholder_analysis_agent", state),
            response_format=AnalisisParticipantesOutput,
            name="stakeholder_analysis_agent",
        )
        
        result = stakeholder_analysis_agent_builder.invoke(state, config)
        
        return Command(
            update={
                "participantes": result.get("structured_response").participantes,
            },
            goto="population_analysis"
        )
    
    def population_analysis(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["objective_analysis"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini
        
        population_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_population_analysis_agent,
            prompt=lambda state: apply_prompt_template("population_analysis_agent", state),
            response_format=AnalisisPoblacion,
            name="population_analysis_agent",
        )
        
        result = population_analysis_agent_builder.invoke(state, config)
        
        return Command(
            update={
                "poblacion_afectada": result.get("structured_response").poblacion_afectada,
                "poblacion_objetivo": result.get("structured_response").poblacion_objetivo,
                "caracteristicas_demograficas_objetivo": result.get("structured_response").caracteristicas_demograficas_objetivo,
                "enfoque_diferencial": result.get("structured_response").enfoque_diferencial,
                "cumple_porcentaje_vinculacion_diferencial": result.get("structured_response").cumple_porcentaje_vinculacion_diferencial,
            },
            goto="objective_analysis"
        )
    
    def objective_analysis(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["alternative_analysis"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.o4mini
        
        objective_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_objective_analysis_agent,
            prompt=lambda state: apply_prompt_template("objective_analysis_agent", state),
            response_format=AnalisisDeObjetivos,
            name="objective_analysis_agent",
        )
        
        result = objective_analysis_agent_builder.invoke(state, config)
        
        return Command(
            update={
                "objetivo_general": result.get("structured_response").objetivo_general,
                "objetivos_especificos": result.get("structured_response").objetivos_especificos,
                "arbol_de_objetivos": result.get("structured_response").arbol_de_objetivos,
            },
            goto="alternative_analysis"
        )
    
    def alternative_analysis(self, state: AnalyticalCoreState, config: RunnableConfig) -> Command[Literal["__end__"]]:
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.o4mini
        
        alternative_analysis_agent_builder = create_react_agent(
            create_llm_model(model=agent_model),
            tools=self.tools_alternative_analysis_agent,
            prompt=lambda state: apply_prompt_template("alternative_analysis_agent", state),
            response_format=AnalisisDeAlternativas,
            name="alternative_analysis_agent",
        )
        
        result = alternative_analysis_agent_builder.invoke(state, config)
        
        return Command(
            update={
                "alternativas": result.get("structured_response").alternativas, 
                "analisis_tecnico_seleccionada": result.get("structured_response").analisis_tecnico_seleccionada,
            },
            goto="__end__"
        )
    
    def build_graph(self):
        builder = StateGraph(AnalyticalCoreState)
        builder.set_entry_point("plan_desarrollo_vectorstore")
        builder.add_node("plan_desarrollo_vectorstore", self.plan_desarrollo_vectorstore)
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
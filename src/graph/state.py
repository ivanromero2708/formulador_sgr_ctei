from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Dict, List, Optional, Any, Literal, Annotated # Ensured Annotated is here
from pydantic import BaseModel, Field
import operator

# Pydantic Models for State Variables

class PerfilEntidad(BaseModel):
    nombre: str = Field(description="Nombre de la entidad")
    tipo: Literal["Proponente", "Aliado"] = Field(description="Tipo de entidad")
    
    areas_expertise_relevante: List[str] = Field(default_factory=list, description="Áreas de expertise relevantes")
    capacidades_tecnicas: List[str] = Field(default_factory=list, description="Capacidades técnicas relevantes")
    lineas_investigacion_relevantes: List[str] = Field(default_factory=list, description="Líneas de investigación relevantes de la institución")
    logros_relevantes: List[str] = Field(default_factory=list, description="Logros relevantes de la institución relacionados con las líneas temáticas del proyecto")
    
    experiencia_proyectos_relacionados: List[str] = Field(default_factory=list, description="Experiencia en proyectos relacionados")

class EntidadProponente(BaseModel):
    """Datos de la entidad proponente del proyecto"""
    nombre: str = Field(description="Nombre de la entidad líder")
    tipo: Optional[str] = Field(None, description="Tipo de entidad (UES, Centro I+D, Empresa, etc.)")
    datos_contacto: Dict[str, str] = Field(default_factory=dict, description="Datos de contacto oficial")

class Alianza(BaseModel):
    """Información de entidades aliadas en el proyecto"""
    nombre: str = Field(description="Nombre de la entidad")
    rol: str = Field(description="Rol en el proyecto (ejecutor, co-ejecutor, aliado)")
    tipo: Optional[str] = Field(None, description="Tipo de entidad")

class LineaTematica(BaseModel):
    """Información sobre líneas temáticas y tipologías (Configuración TDR)"""
    macro_linea: str = Field(description="Macro-línea temática")
    sub_linea: Optional[str] = Field(None, description="Sub-línea temática")

class DemandaTerritorial(BaseModel):
    """Información sobre demandas territoriales (Catálogo TDR o elección usuario)"""
    ID: Optional[str] = Field(None, description="Código del reto priorizado")
    departamento: Optional[str] = Field(None, description="Departamento del reto")
    reto: str = Field(description="Nombre del reto")
    demanda_territorial: str = Field(description="Descripción de la demanda territorial asociada al reto priorizado")

class CriterioEvaluacion(BaseModel):
    """Criterios de evaluación del proyecto (Configuración TDR)"""
    ponderacion_merito: Optional[float] = Field(None, description="Ponderación del mérito")
    ponderacion_pertinencia: Optional[float] = Field(None, description="Ponderación de la pertinencia")
    ponderacion_impacto: Optional[float] = Field(None, description="Ponderación del impacto")
    ponderacion_viabilidad: Optional[float] = Field(None, description="Ponderación de la viabilidad")
    penalizaciones: List[Dict[str, Any]] = Field(default_factory=list, description="Penalizaciones aplicables")
    bonificaciones: List[Dict[str, Any]] = Field(default_factory=list, description="Bonificaciones aplicables")

class IdeaProyecto(BaseModel):
    """Idea base del proyecto (Input Usuario)"""
    titulo_provisional: str = Field(description="Título provisional del proyecto")
    problema_descripcion: str = Field(description="Problema o percepción inicial")
    tecnologia_enfoque_propuesto: str = Field(description="Tecnología o enfoque propuesto")

class PresupuestoEstimadoUsuario(BaseModel):
    """Presupuesto global estimado (Input Usuario)"""
    monto_sgr_solicitado: float = Field(description="Monto SGR solicitado en COP")
    porcentaje_contrapartida_disponible: float = Field(description="Porcentaje de contrapartida disponible")


class ConceptoProyectoGenerado(BaseModel):
    """Concepto de proyecto generado por el sistema (Ideador)"""
    id_concepto: str = Field(description="Identificador único del concepto")
    titulo_sugerido: str = Field(description="Título sugerido para el proyecto")
    problema_abordado: str = Field(description="Descripción del problema que aborda")
    objetivo_general: str = Field(description="Objetivo general del proyecto")
    objetivos_especificos: List[str] = Field(default_factory=list, description="Objetivos específicos")
    resultados_esperados: List[str] = Field(default_factory=list, description="Resultados e impactos esperados")
    linea_tematica_asociada: Optional[LineaTematica] = Field(None, description="Línea temática del TDR a la que se alinea")
    demanda_territorial_asociada: Optional[DemandaTerritorial] = Field(None, description="Demanda territorial del TDR que atiende")
    presupuesto_estimado_sgr: Optional[float] = Field(None, description="Presupuesto SGR estimado para este concepto")
    duracion_estimada_meses: Optional[int] = Field(None, description="Duración estimada en meses para este concepto")

class MMLNivel(BaseModel):
    """
    Representa un nivel jerárquico (Fin, Propósito, Producto/Output, o Actividad) 
    en la Matriz de Marco Lógico. Contiene los elementos comunes a cada fila de la MML.
    """
    # id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador único para el nivel.") # Import uuid if used
    resumen_narrativo: str = Field(description="Descripción concisa de qué se pretende lograr o entregar en este nivel.")
    indicadores: List[str] = Field(default_factory=list, description="Indicadores objetivamente verificables (cuantitativos o cualitativos) para medir el logro.")
    medios_verificacion: List[str] = Field(default_factory=list, description="Fuentes de información y métodos para recabar los datos de los indicadores.")
    supuestos: List[str] = Field(default_factory=list, description="Factores externos, condiciones o riesgos que deben gestionarse o cumplirse para que se materialicen los vínculos causales al siguiente nivel superior.")

class MMLProductoOutput(MMLNivel):
    """
    Representa un Producto/Output específico del proyecto. 
    Hereda los campos de MMLNivel (resumen_narrativo, indicadores, etc., para el Producto/Output) 
    e incluye una lista de Actividades asociadas necesarias para su consecución.
    """
    actividades: List[MMLNivel] = Field(default_factory=list, description="Lista de Actividades detalladas que se llevarán a cabo para generar este Producto/Output. Cada actividad también es un MMLNivel.")

class MarcoLogicoEstructura(BaseModel):
    """
    Estructura completa de la Matriz de Marco Lógico (MML) del proyecto,
    organizada jerárquicamente.
    """
    fin: Optional[MMLNivel] = Field(None, description="Nivel de Fin (Impacto): El objetivo de desarrollo a largo plazo al que el proyecto contribuye.")
    proposito: Optional[MMLNivel] = Field(None, description="Nivel de Propósito (Outcome): El cambio directo o resultado intermedio que el proyecto busca generar.")
    productos_outputs: List[MMLProductoOutput] = Field(default_factory=list, description="Lista de Productos/Outputs (Componentes): Los bienes y servicios tangibles que el proyecto producirá. Cada Producto/Output contiene sus propias actividades, indicadores, medios y supuestos.")

class PresupuestoRubro(BaseModel):
    codigo: Optional[str] = None
    descripcion: str
    unidad: Optional[str] = None
    cantidad: Optional[float] = None
    valor_unitario_sgr: Optional[float] = None
    valor_total_sgr: Optional[float] = None
    valor_unitario_contrapartida: Optional[float] = None
    valor_total_contrapartida: Optional[float] = None
    fuente_verificacion: Optional[str] = None # Para estudio de mercado

class PresupuestoDetallado(BaseModel):
    """Presupuesto detallado del proyecto"""
    rubros: List[PresupuestoRubro] = Field(default_factory=list)
    total_sgr: Optional[float] = None
    total_contrapartida_efectivo: Optional[float] = None
    total_contrapartida_especie: Optional[float] = None
    total_general: Optional[float] = None
    # Podría incluir cronograma de desembolsos si es necesario

class DocumentoTecnicoSeccion(BaseModel):
    """Una sección del documento técnico"""
    numero_seccion: str = Field(description="Ej: 1.1, 2.3.4")
    titulo_seccion: str
    contenido_generado: Optional[str] = Field(None, description="Contenido textual de la sección")
    # Podría tener subsecciones o tablas estructuradas

class DocumentoTecnicoCompleto(BaseModel):
    """Documento técnico completo del proyecto"""
    secciones: List[DocumentoTecnicoSeccion] = Field(default_factory=list)
    # Metadatos como versión, fecha, etc.

# Main Agent State

# Pydantic models for structured node outputs
from langchain_core.messages.base import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import field_validator
from typing import Annotated, Sequence
import operator

class CoordinadorGeneralOutput(BaseModel):
    """
    Structured output for the CoordinadorGeneral node.
    Determines the next step and can update initial parameters.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # === USER INPUTS (Recibido de SchemaEntrada) ===
    tdr_document_path: Optional[str] = Field(default=None, description="Path al documento TDR principal (PDF, DOCX)")
    additional_documents_paths: List[str] = Field(default_factory=list, description="Paths a otros documentos de entrada (guías sectoriales, anexos TDR)")
    
    # Datos específicos del usuario procesados desde raw_user_input_data
    departamento: str = Field(description="Departamento seleccionado para el proyecto")
    entidad_proponente_usuario: Optional[EntidadProponente] = Field(description="Información básica de la entidade proponente del proyecto")
    alianzas_usuario: Optional[List[Alianza]] = Field(description="Listado de entidades aliadas del proyecto")
    demanda_territorial_seleccionada_usuario: Optional[DemandaTerritorial] = Field(description="Departamento seleccionado para el proyecto")
    idea_base_proyecto_usuario: Optional[IdeaProyecto] = Field(description="Idea base del proyecto")
    duracion_proyecto_usuario: str = Field(description="Duración deseada del proyecto en meses")
    presupuesto_estimado_usuario: Optional[PresupuestoEstimadoUsuario] = Field(description="Presupuesto estimado del proyecto")
    
    hand_off_to_planner: bool

    class Config:
        arbitrary_types_allowed = True

    @field_validator("messages", mode="before")
    def ensure_message_type(cls, value):
        # Procesa cada elemento de la lista manualmente.
        if isinstance(value, list):
            nuevos = []
            for item in value:
                # Si el item es un diccionario y no tiene la clave "type", se asigna "ai" por defecto.
                if isinstance(item, dict) and "type" not in item:
                    item["type"] = "ai"
                nuevos.append(item)
            return nuevos
        return value
    


class SeccionTDR(BaseModel):
    nombre: Literal[
        "objetivo_tdr",
        "dirigida_a_tdr",
        "demandas_territoriales_tdr",
        "lineas_tematicas_tdr",
        "alcance_convocatoria_tdr",
        "orientaciones_vinculacion_talento_humano_tdr",
        "requisitos_proyecto_tdr",
        "contenido_proyecto_tdr",
        "duracion_financiacion_tdr",
        "criterios_evaluacion_proyectos_tdr",
    ] = Field(description="Nombre de la sección de los TDR")
    contenido: str = Field(description="Contenido de la sección de los TDR")

class FormuladorCTeIAgent(AgentState):
    """State for Project Formulator Agentic workflow"""

    # === USER INPUTS (Recibido de SchemaEntrada) ===
    tdr_document_path: Optional[str] = Field(default=None, description="Path al documento TDR principal (PDF, DOCX)")
    additional_documents_paths: List[str] = Field(default_factory=list, description="Paths a otros documentos de entrada (guías sectoriales, anexos TDR)")
    
    # Datos específicos del usuario procesados desde raw_user_input_data
    departamento: str = Field(description="Departamento seleccionado para el proyecto")
    entidad_proponente_usuario: Optional[EntidadProponente] = Field(description="Información básica de la entidade proponente del proyecto")
    alianzas_usuario: Optional[List[Alianza]] = Field(description="Listado de entidades aliadas del proyecto")
    demanda_territorial_seleccionada_usuario: Optional[DemandaTerritorial] = Field(description="Departamento seleccionado para el proyecto")
    idea_base_proyecto_usuario: Optional[IdeaProyecto] = Field(description="Idea base del proyecto")
    duracion_proyecto_usuario: str = Field(description="Duración deseada del proyecto en meses")
    presupuesto_estimado_usuario: Optional[PresupuestoEstimadoUsuario] = Field(description="Presupuesto estimado del proyecto")

    # === TDR PARSED DATA (Poblado por TDRParsing) ===
    tdr_text_content: Optional[str] = Field(default=None, description="Contenido textual extraído del TDR")
    # Variables extraídas y estructuradas del TDR
    secciones_tdr: Annotated[List[SeccionTDR], operator.add] = Field(default_factory=list, description="Secciones del TDR") # Changed ... to default_factory=list
    
    perfil_entidades: List[PerfilEntidad]
    
    # === PROJECT IDEATION (Poblado por ProjectStructure) ===
    conceptos: Annotated[List[ConceptoProyectoGenerado], operator.add] = Field(default_factory=list, description="Lista de ≥3 conceptos de proyecto generados")
    conceptos_enriquecidos: Annotated[List[ConceptoProyectoGenerado], operator.add] = Field(default_factory=list, description="Lista de ≥3 conceptos de proyecto generados")
    
    # === PROJECT SELECTION (Poblado por ProjectSelection) ===
    concepto_proyecto_seleccionado_id: Optional[str] = Field(default=None, description="ID del concepto de proyecto elegido por el usuario")
    proyecto_seleccionado_detalle: Optional[ConceptoProyectoGenerado] = Field(default=None, description="Detalle completo del proyecto seleccionado")
    concepto_seleccionado: Optional[ConceptoProyectoGenerado] = Field(default=None, description="Concepto seleccionado por el usuario")
    
    # === DETAILED STRUCTURING (Poblado por nodos subsecuentes) ===
    marco_logico_final: Optional[MarcoLogicoEstructura] = Field(default=None)
    presupuesto_detallado_final: Optional[PresupuestoDetallado] = Field(default=None)
    documento_tecnico_final: Optional[DocumentoTecnicoCompleto] = Field(default=None)

    # === RENDERED OUTPUTS (Poblado por RenderDocumentation) ===
    documento_tecnico_docx_path: Optional[str] = Field(default=None, description="Path al DOCX final del Documento Técnico")
    presupuesto_xlsx_path: Optional[str] = Field(default=None, description="Path al XLSX final del Presupuesto")

    class Config:
        arbitrary_types_allowed = True
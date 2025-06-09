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


class GrupoInvestigacionProyecto(BaseModel):
    nombre_grupo: str = Field(..., description="Nombre del grupo de investigación")
    entidad: str = Field(..., description="Entidad a la que pertenece el grupo de investigación")
    lineas_investigacion: List[str] = Field(..., description="Lineas de investigación del grupo de investigación")
    numero_investigadores_formacion: str = Field(..., description="Número de investigadores y su nivel de formación")
    numero_estudiantes_vinculacion: int = Field(..., description="Número de estudiantes que puede vincular el grupo de investigación")
    contribucion_lineas_demandas: str = Field(..., description="Contribución de la(s) línea(s) al abordaje del las demanda(s) territoriales y los Alcances temáticos")

class LocalizacionProyecto(BaseModel):
    regiones: List[str] = Field(..., description="Nombre de las dos (2) regiones geográficas del SGR de donde será ejecutado el proyecto")
    departamentos: List[str] = Field(..., description="Nombre del/los departamento(s) objeto del proyecto")
    municipios: List[str] = Field(..., description="Nombre(s) del/los municipios(s) y (Si aplica), indique si son municipios categorizados como PDET, ZOMAC o incluye actores diferenciales para el cambio.")
    centro_poblados: Optional[List[str]] = Field(None, description="Incluya (Urbano / Rural) (Si aplica)")
    resguardos: Optional[List[str]] = Field(None, description="Incluya el nombre o No aplica (según el proyecto)")

class IdentificacionProyecto(BaseModel):
    nombre_proyecto: str = Field(..., description="Nombre del proyecto")
    localizacion_proyecto: LocalizacionProyecto = Field(..., description="Localización del proyecto")
    demandas_territoriales: List[str] = Field(..., description="Demandas territoriales que se atenderán con el proyecto")    
    lineas_tematicas: List[str] = Field(..., description="Indique la(s) línea(s) temática(s)  que trabajará en el desarrollo de su propuesta y conexión con las regiones para las que solicita los recursos.")


class ProblemTreeState(BaseModel):
    problema_central: str = Field(..., description="Enunciado del problema central")
    causas_directas: List[str] = Field(..., description="Listado de causas directas del problema")
    causas_indirectas: List[str] = Field(..., description="Listado de causas indirectas (raíces profundas)")
    efectos_directos: List[str] = Field(..., description="Listado de efectos directos del problema")
    efectos_indirectos: List[str] = Field(..., description="Listado de efectos indirectos (consecuencias a largo plazo)")

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ==============================================================================
# 1. ENUMERACIONES (TIPOS DE DATOS CATEGÓRICOS)
# ==============================================================================

class PosicionParticipante(str, Enum):
    """
    Define la categoría o posición del participante en el proyecto.
    El uso de Enum previene errores de tipeo y hace el código más claro.
    """
    BENEFICIARIO = "Beneficiario"
    COOPERANTE = "Cooperante"
    OPONENTE = "Oponente"
    PERJUDICADO = "Perjudicado"

class TipoActor(str, Enum):
    """
    Clasificación del actor según su ámbito o naturaleza.
    """
    DEPARTAMENTAL = "Departamental"
    MUNICIPAL = "Municipal"
    NACIONAL = "Nacional"
    PRIVADO = "Privado"
    ACADEMIA = "Academia"
    SOCIEDAD_CIVIL = "Sociedad Civil"
    OTRO = "Otro"


# ==============================================================================
# 2. MODELO PARA UN PARTICIPANTE INDIVIDUAL
# ==============================================================================

class Participante(BaseModel):
    """
    Representa a una persona o entidad individual involucrada en el proyecto,
    correspondiendo a una fila en la tabla de análisis.
    """
    tipo_actor: TipoActor = Field(
        ...,
        description="Clasificación general del actor (ej. Departamental, Privado, Otro)."
    )
    entidad: str = Field(
        ...,
        min_length=3,
        description="Nombre de la persona, grupo o institución."
    )
    posicion: PosicionParticipante = Field(
        ...,
        description="El rol principal que asume la entidad frente al proyecto."
    )
    intereses_expectativas: str = Field(
        ...,
        description="Descripción de los intereses y expectativas de la entidad."
    )
    contribuciones: Optional[List[str]] = Field(
        default=None,
        description="Lista de contribuciones o gestiones. Aplica solo para Beneficiarios y Cooperantes."
    )

    @field_validator('contribuciones')
    @classmethod
    def validar_contribuciones_por_posicion(cls, v, info):
        """
        Validador para asegurar que solo los Beneficiarios y Cooperantes tengan contribuciones.
        """
        # Si el campo 'posicion' no está presente en los datos, no podemos validar.
        if 'posicion' not in info.data:
            return v
        
        posicion = info.data['posicion']
        if posicion in [PosicionParticipante.OPONENTE, PosicionParticipante.PERJUDICADO] and v is not None:
            raise ValueError(f"El campo 'contribuciones' no es aplicable para la posición '{posicion.value}'. Debe ser nulo.")
        if posicion in [PosicionParticipante.BENEFICIARIO, PosicionParticipante.COOPERANTE] and v is None:
             raise ValueError(f"El campo 'contribuciones' es requerido para la posición '{posicion.value}'.")
        return v

from enum import Enum
from typing import List, Optional

from pydantic import (BaseModel, Field, PositiveInt, NonNegativeFloat,
                      model_validator, field_validator)

# ==============================================================================
# 1. MODELOS DE SOPORTE Y ENUMERACIONES
# ==============================================================================

class FuenteValidacion(BaseModel):
    """
    Representa una fuente de datos usada para validar información poblacional,
    como se exige en los apartados 11.1 y 11.2.
    """
    nombre_fuente: str = Field(
        ...,
        description="Nombre de la fuente oficial (ej. 'Censo DANE 2018', 'Encuesta SISBEN IV')."
    )
    referencia: str = Field(
        ...,
        description="Referencia específica, como un enlace web, número de tabla o documento para su validación."
    )

class GrupoPoblacionalDiferencial(str, Enum):
    """
    Categorías de los actores diferenciales para el cambio, según la tabla de enfoque diferencial.
    """
    GENERO = "Género"
    ETNICO = "Étnico (Indígena, Afro, Raizal, Palenquero, Rom)"
    SITUACION_DISCAPACIDAD = "Situación de Discapacidad"
    VULNERABLE = "Población Vulnerable"

class ParticipacionActorDiferencial(BaseModel):
    """
    Representa una fila de la tabla de participación de actores diferenciales.
    """
    grupo_poblacional: GrupoPoblacionalDiferencial = Field(
        ...,
        description="Grupo al que pertenece el actor diferencial."
    )
    actividad_cadena_valor: str = Field(
        ...,
        description="Actividad específica en la que participarán los actores."
    )
    valor_actividad: NonNegativeFloat = Field(
        ...,
        description="Valor en pesos de la actividad a desarrollar con recursos del proyecto."
    )
    descripcion_participacion: str = Field(
        ...,
        description="Detalle de cómo los actores participan activamente en la actividad."
    )


# ==============================================================================
# 2. MODELOS PRINCIPALES DE SUB-SECCIONES
# ==============================================================================

class PoblacionAfectada(BaseModel):
    """Modelo para la sección 11.1. Población Afectada."""
    cantidad: PositiveInt = Field(
        ...,
        description="Número total de la población afectada general."
    )
    determinacion: str = Field(
        ...,
        description="Texto que explica cómo se determinó y calculó esta población."
    )
    fuente: FuenteValidacion = Field(
        ...,
        description="Fuente oficial que soporta la existencia y tamaño de esta población."
    )

class PoblacionObjetivo(BaseModel):
    """Modelo para la sección 11.2. Población Objetivo."""
    cantidad: PositiveInt = Field(
        ...,
        description="Número de la población sobre la cual directamente hará intervención el proyecto."
    )
    criterios_seleccion: str = Field(
        ...,
        description="Texto que explica los criterios de selección claramente definidos para focalizar la población."
    )
    fuente: FuenteValidacion = Field(
        ...,
        description="Fuente oficial que soporta la existencia y tamaño de esta población."
    )
    
class EnfoqueDiferencial(BaseModel):
    """Modelo para la sección de Enfoque Diferencial dentro del apartado 11.3."""
    aporta_a_solucion: bool = Field(
        ...,
        description="Indica si el proyecto aporta a la solución de problemáticas de enfoque diferencial."
    )
    descripcion_actores_diferenciales: Optional[str] = Field(
        default=None,
        description="Descripción de los actores diferenciales para el cambio que participarán."
    )
    participacion_actores: Optional[List[ParticipacionActorDiferencial]] = Field(
        default=None,
        description="Tabla detallada de la participación de los actores diferenciales."
    )

    @field_validator('descripcion_actores_diferenciales', 'participacion_actores')
    @classmethod
    def validar_campos_requeridos(cls, v, info):
        """Si el proyecto aporta a la solución, la descripción y la tabla son obligatorias."""
        if info.data.get('aporta_a_solucion') and v is None:
            raise ValueError("Este campo es obligatorio si el proyecto aporta a la solución de enfoque diferencial.")
        return v


import re
from enum import Enum
from typing import List

from pydantic import (BaseModel, Field, field_validator, model_validator)

# ==============================================================================
# 1. MODELOS DE SOPORTE Y ENUMERACIONES
# ==============================================================================

class TipoIndicador(str, Enum):
    """
    Tipo de indicador para el objetivo general, como lo exige el documento.
    """
    IMPACTO = "Impacto"
    RESULTADO = "Resultado"

class Indicador(BaseModel):
    """
    Representa un indicador de cumplimiento para el objetivo general.
    """
    nombre: str = Field(..., description="Nombre claro y conciso del indicador.")
    tipo: TipoIndicador = Field(..., description="El tipo de indicador: de impacto o de resultado.")
    descripcion: str = Field(..., description="Explica qué mide el indicador y cómo se relaciona con el objetivo.")


# ==============================================================================
# 2. MODELOS PRINCIPALES DE SUB-SECCIONES
# ==============================================================================

class ObjetivoGeneral(BaseModel):
    """Modelo para la sección 12.1. Objetivo General y sus indicadores."""
    enunciado: str = Field(
        ...,
        description="Enunciado que define de manera concreta el problema, iniciando con un verbo en infinitivo."
    )
    indicadores: List[Indicador] = Field(
        ...,
        min_length=1,
        description="Lista de los indicadores que medirán el cumplimiento del objetivo general."
    )

    @field_validator('enunciado')
    @classmethod
    def validar_inicio_con_verbo_infinitivo(cls, v: str) -> str:
        """Valida que el enunciado del objetivo general comience con un verbo en infinitivo (ar, er, ir)."""
        # Expresión regular simple para verificar si la primera palabra termina en ar, er, o ir.
        if not re.match(r'^\w+(ar|er|ir)\b', v.lower().strip()):
            raise ValueError('El enunciado del objetivo general debe comenzar con un verbo en infinitivo (ej. "Desarrollar", "Implementar").')
        return v

class ArbolDeObjetivos(BaseModel):
    """
    Modelo para la sección 12.3, que representa la estructura jerárquica del árbol de objetivos.
    """
    fines_indirectos: List[str] = Field(..., description="Los fines o impactos a más largo plazo del proyecto.")
    fines_directos: List[str] = Field(..., description="Los efectos directos que se logran al cumplir el objetivo general.")
    objetivo_general_enunciado: str = Field(..., description="El enunciado del objetivo general (debe coincidir con la sección 12.1).")
    objetivos_especificos_enunciados: List[str] = Field(..., description="Los enunciados de los objetivos específicos (deben coincidir con la sección 12.2).")
    medios: List[str] = Field(..., description="Las acciones o productos directos que constituyen los objetivos específicos.")


from enum import Enum
from typing import List

from pydantic import (BaseModel, Field, model_validator)

# ==============================================================================
# 1. MODELOS DE SOPORTE Y ENUMERACIONES
# ==============================================================================

class CriterioEvaluacion(str, Enum):
    """
    Criterios de evaluación que se pueden aplicar a cada alternativa.
    """
    RENTABILIDAD = "Rentabilidad"
    COSTO_EFICIENCIA = "Costo-Eficiencia"
    COSTO_MINIMO = "Costo Mínimo"

class Evaluacion(BaseModel):
    """
    Representa la evaluación realizada a una alternativa,
    según la segunda columna de la tabla.
    """
    criterio: CriterioEvaluacion = Field(
        ...,
        description="El criterio principal utilizado para la evaluación."
    )
    es_positiva: bool = Field(
        ...,
        description="El resultado de la evaluación (Sí/No)."
    )


# ==============================================================================
# 2. MODELO PARA UNA ALTERNATIVA INDIVIDUAL
# ==============================================================================

class Alternativa(BaseModel):
    """
    Representa una alternativa de solución individual, correspondiente a una fila de la tabla.
    """
    nombre: str = Field(
        ...,
        min_length=5,
        description="Nombre claro y descriptivo de la alternativa."
    )
    evaluacion: Evaluacion = Field(
        ...,
        description="La evaluación técnica o financiera de la alternativa."
    )
    es_seleccionada: bool = Field(
        ...,
        description="Indica si esta es la alternativa que se eligió para implementar en el proyecto."
    )
    justificacion: str = Field(
        ...,
        min_length=20,
        description="Breve justificación que explica por qué la alternativa fue seleccionada o descartada."
    )




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
    
    # === Phase 0: Project Initiation and Preliminary Information Gathering ===
    identificacion_proyecto: Optional[IdentificacionProyecto] = Field(default=None, description="Identificación del proyecto")
    palabras_clave: Optional[str] = Field(default=None, description="Palabras clave del proyecto")
    antecedentes: Optional[str] = Field(default=None, description="Antecedentes identificados en relación con la problemática, necesidad u oportunidad a abordar en el marco del proyecto. Adicionalmente, presentar el desarrollo previo de iniciativas a nivel internacional, nacional, departamental o municipal en el marco de la temática del proyecto; así como los resultados de éstas, que ilustran la pertinencia de desarrollar el proyecto que se presenta. Nota: En lo posible relacione la información anterior con el contexto regional y departamental.")
    idoneidad_trayectoria_proponentes: Optional[str] = Field(default=None, description = "Descripción de los aportes de los integrantes de la alianza para la contribución a la consecución de los objetivos y actividades del proyecto. Los aportes de los integrantes de la alianza deben ser individuales y contemplar al menos uno o más de uno de los siguientes aportes: financieros, técnicos /tecnológicos y de talento humano de alto nivel. Esto debe guardar total coherencia con la información suministrada en la Carta aval, compromiso institucional y modelo de gobernanza y en el presupuesto del proyecto.")
    grupos_investigacion_proyecto: Optional[List[GrupoInvestigacionProyecto]] = Field(default=None, description="Grupos de investigación vinculados al proyecto")

    # === Phase 1: Analytical Core ===
    problema_central: Optional[str] = Field(default=None, description="Problema central identificado")
    descripcion_problema: Optional[str] = Field(default=None, description="Descripción del problema central")
    magnitud_problema: Optional[str] = Field(default=None, description="Magnitud del problema central")
    arbol_problema: Optional[ProblemTreeState] = Field(default=None, description="Árbol de problemas")
    participantes: List[Participante] = Field(..., description="Lista completa de las entidades analizadas.")
    poblacion_afectada: PoblacionAfectada = Field(..., description="Detalles de la sección 11.1.")
    poblacion_objetivo: PoblacionObjetivo = Field(..., description="Detalles de la sección 11.2.")    
    caracteristicas_demograficas_objetivo: str = Field(..., description="Texto que caracteriza a las personas que conforman la población objetivo y su perfil.")
    enfoque_diferencial: EnfoqueDiferencial = Field(..., description="Análisis detallado del enfoque diferencial del proyecto, según el apartado 11.3.")
    objetivo_general: ObjetivoGeneral = Field(..., description="Sección 12.1 detallada.")
    objetivos_especificos: List[str] = Field(..., min_length=1, description="Lista de enunciados de los objetivos específicos (Sección 12.2).")
    arbol_de_objetivos: ArbolDeObjetivos = Field(..., description="Estructura completa del árbol de objetivos (Sección 12.3).")
    alternativas: List[Alternativa] = Field(..., min_length=2, description="Lista de las alternativas identificadas (se requiere un mínimo de 2).")
    analisis_tecnico_seleccionada: str = Field(..., min_length=50, description="Análisis detallado (técnico, financiero, etc.) que justifica la selección de una alternativa y el descarte de las demás.")
    
    # === RENDERED OUTPUTS (Poblado por RenderDocumentation) ===
    documento_tecnico_docx_path: Optional[str] = Field(default=None, description="Path al DOCX final del Documento Técnico")
    presupuesto_xlsx_path: Optional[str] = Field(default=None, description="Path al XLSX final del Presupuesto")

    class Config:
        arbitrary_types_allowed = True
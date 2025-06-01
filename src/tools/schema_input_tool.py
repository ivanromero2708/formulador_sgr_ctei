from pydantic import BaseModel, Field
from typing import List, Optional
from src.graph.state import EntidadProponente, Alianza, DemandaTerritorial, IdeaProyecto, PresupuestoEstimadoUsuario

class SchemaInputTool(BaseModel):
    """Modelo de datos requerido para iniciar el proceso de Estructuración de proyectos de CTeI"""
    # === USER INPUTS (Recibido de SchemaEntrada) ===
    tdr_document_path: Optional[str] = Field(default=None, description="Path al documento TDR principal (PDF, DOCX)")
    additional_documents_paths: List[str] = Field(default_factory=list, description="Paths a otros documentos de entrada (guías sectoriales, anexos TDR)")
    
    # Datos específicos del usuario procesados desde raw_user_input_data
    entidad_proponente_usuario: Optional[EntidadProponente] = Field(default=None)
    alianzas_usuario: Optional[List[Alianza]] = Field(default_factory=list)
    demanda_territorial_seleccionada_usuario: Optional[DemandaTerritorial] = Field(default=None)
    idea_base_proyecto_usuario: Optional[IdeaProyecto] = Field(default=None)
    duracion_proyecto_usuario: str = Field(default=None) # Solo meses_deseados_usuario aquí
    presupuesto_estimado_usuario: Optional[PresupuestoEstimadoUsuario] = Field(default=None)

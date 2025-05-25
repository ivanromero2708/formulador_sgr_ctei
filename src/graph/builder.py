from langgraph.graph import StateGraph
from src.graph.state import FormuladorCTeIAgent
from src.graph import (
    SchemaEntradaBuilder,
    CoordinadorGeneral,
    TDRVectorStore,
    TDRParsingAgent,
    ProjectStructure,
    ProjectSelection,
    LogicFrameworkStructure,
    BudgetCalculation,
    TechnicalDocumentWriting,
    RenderDocumentation,
)

from dotenv import load_dotenv

# Cargar variables de ambiente
load_dotenv()

## Graph Initialization
builder = StateGraph(FormuladorCTeIAgent)

## Schema Builder
builder.set_entry_point("schema_entrada")
builder.add_node("schema_entrada", SchemaEntradaBuilder().run)
builder.add_node("coordinador_general", CoordinadorGeneral().run)

## Analisis documentos de entrada
builder.add_node("tdr_vectorstore", TDRVectorStore().run)

## Agente RAG de TDR parsing
builder.add_node("tdr_parsing_agent", TDRParsingAgent().run)

## Estructuracion de proyectos
builder.add_node("project_structure", ProjectStructure().run)

## Seleccion de proyecto
builder.add_node("project_selection", ProjectSelection().run)

## Estructuracion marco logico
builder.add_node("logic_framework_structure", LogicFrameworkStructure().run)

## Calculo de presupuesto
builder.add_node("budget_calculation", BudgetCalculation().run)

## Escritura de documento técnico
builder.add_node("technical_document_writing", TechnicalDocumentWriting().run)

## Renderizado de la documentación
builder.add_node("render_documentation", RenderDocumentation().run)

## Compile Graph
workflow_formulador_ctei_graph = builder.compile()
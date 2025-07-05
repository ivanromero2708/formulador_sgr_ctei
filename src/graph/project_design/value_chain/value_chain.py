# ────────────────────────────────────────────────────────────────
#  Archivo: src/graph/project_design/project_design.py
# ────────────────────────────────────────────────────────────────
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.types import Command, Send
from langgraph.prebuilt import create_react_agent
from src.tools import vec_retriever_ctei
from src.config.configuration import MultiAgentConfiguration
from src.graph.state import FormuladorCTeIAgent
from src.llms.llm import create_llm_model
from pydantic import Field, BaseModel
from typing import Literal, List, Optional, Annotated
from langchain_core.runnables import RunnableConfig
from json import dumps
import operator
import pandas as pd
from pathlib import Path

from src.prompts.prompts_project_design import (
    PROMPT_GENERACION_PRODUCTOS,
    SYSTEM_PROMPT_PRODUCT_MATCHING,
)

# ─── NUEVOS modelos importados ─────────────────────────────────
from src.graph.state import ActivitiesEDT, ValueChain, ActivityEDT, ValueChainItem


# ────────────────────────────────────────────────────────────────
#  Modelos pre-existentes (ProductoMGA, ProductosMGA, etc.)
# ────────────────────────────────────────────────────────────────
class ProductoMGA(BaseModel):
    sector:              str            = Field(..., alias="Sector")
    nombre_sector:       str            = Field(..., alias="Nombre del Sector")
    codigo_programa:     str            = Field(..., alias="Código del Programa")
    nombre_programa:     str            = Field(..., alias="Nombre del Programa")
    codigo_producto:     str            = Field(..., alias="Código del Producto")
    producto:            str            = Field(..., alias="Producto")
    descripcion:         str            = Field(..., alias="Descripción")
    medido_a_traves_de:  str            = Field(..., alias="Medido a través de")
    codigo_indicador:    str            = Field(..., alias="Código del Indicador de Producto")
    indicador_producto:  str            = Field(..., alias="Indicador de Producto")
    unidad_medida:       str            = Field(..., alias="Unidad de medida")
    indicador_principal: bool           = Field(..., alias="Indicador Principal")
    es_nacional:         bool           = Field(..., alias="Es Nacional")
    es_territorial:      bool           = Field(..., alias="Es Territorial")
    ods:                 List[str]      = Field(..., alias="Objetivos de Desarrollo Sostenible - ODS")
    meta_ods:            str            = Field(..., alias="Meta ODS")
    tipologia_general:   str            = Field(..., alias="Tipología General")
    tipologia_d:         bool           = Field(..., alias="Tipología D")
    tipologia_e:         bool           = Field(..., alias="Tipología E")
    tipologia_a:         bool           = Field(..., alias="Tipología A")
    tipologia_b:         bool           = Field(..., alias="Tipología B")
    tipologia_c:         bool           = Field(..., alias="Tipología C")
    tiene_edt:           bool           = Field(..., alias="Tiene EDT")
    edt:                 Optional[str]  = Field(None, alias="EDT")


class ProductosMGA(BaseModel):
    productos_mga: List[ProductoMGA]


class ProductoSugerido(BaseModel):
    producto: str = Field(..., description="Nombre del producto sugerido")
    descripcion: str = Field(..., description="Descripcion del producto sugerido")


class ProductosSugeridos(BaseModel):
    productos_sugeridos: List[ProductoSugerido]


class ProductMatchingState(BaseModel):
    producto_sugerido: ProductoSugerido
    objetivo_general: str
    objetivo_especifico: str


# ────────────────────────────────────────────────────────────────
#  Estado global del grafo (AMPLIADO)
# ────────────────────────────────────────────────────────────────
class ValueChainState(FormuladorCTeIAgent):
    productos_sugeridos: ProductosSugeridos = Field(default_factory=list)
    productos_mga:       Annotated[List[ProductoMGA], operator.add]

    actividades_edt: ActivitiesEDT | None = None   # ← NUEVO
    cadena_valor:    ValueChain   | None = None    # ← NUEVO

    marco_logico:    dict | None = None


# ────────────────────────────────────────────────────────────────
#  Utilidades internas
# ────────────────────────────────────────────────────────────────
def _buscar_actividades_edt(
    descripcion_producto: str,
    excel_path: Path = Path("src/databases/catalogo_edt.xlsx"),
) -> pd.DataFrame:
    """Devuelve las filas del catálogo EDT que 'matchean' la descripción."""
    if not excel_path.exists():
        raise FileNotFoundError(f"Catálogo EDT no encontrado en {excel_path}")

    df = pd.read_excel(excel_path)
    mask = df["Nombre Producto"].str.lower().str.contains(
        descripcion_producto.lower(), na=False
    )
    resultados = df[mask].copy()

    if resultados.empty:
        raise ValueError(
            f"No se encontraron actividades EDT para la descripción '{descripcion_producto}'"
        )
    return resultados


def _df_to_pydantic_list(df: pd.DataFrame) -> List[ActivityEDT]:
    """Convierte un DataFrame EDT -> lista[ActivityEDT]."""
    return [ActivityEDT(**row) for row in df.to_dict(orient="records")]


# ────────────────────────────────────────────────────────────────
#  Clase principal ValueChain (nodos y grafo)
# ────────────────────────────────────────────────────────────────
class ValueChain:
    # ─────────── 1) generate_products ──────────────────────────
    def _generate_products(self, state: ValueChainState, config: RunnableConfig):

        llm_config = MultiAgentConfiguration.from_runnable_config(config)
        llm_model_str = llm_config.o4mini
        llm_model_structured = create_llm_model(llm_model_str).with_structured_output(
            ProductosSugeridos
        )

        objetivo_general = state.get("objetivo_general")
        objetivo_especifico = state.get("objetivo_especifico")

        system_msg = SystemMessage(
            content=PROMPT_GENERACION_PRODUCTOS.format(
                objetivo_general_str=objetivo_general.model_dump_json(indent=2) if objetivo_general else "",
                objetivo_especifico_str=objetivo_especifico,
            )
        )

        human_msg = HumanMessage(
            content="Genera productos asociados a cada uno de los objetivos específicos del proyecto de acuerdo a tus instrucciones."
        )

        productos_sugeridos = llm_model_structured.invoke([system_msg, human_msg])

        goto = [
            Send(
                "product_matcher",
                {
                    "producto_sugerido": ps,
                    "objetivo_general": objetivo_general,
                    "objetivos_especificos": objetivos_especificos,
                },
            )
            for ps in productos_sugeridos.productos_sugeridos
        ]

        return Command(update={"productos_sugeridos": productos_sugeridos}, goto=goto)

    # ─────────── 2) product_matcher ──────────────────────────
    def _product_matching_agent(self, config):
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        agent_model = agent_configuration.gpt41mini

        product_matching_agent_builder = create_react_agent(
            create_llm_model(agent_model),
            tools=[vec_retriever_ctei],
            prompt=SYSTEM_PROMPT_PRODUCT_MATCHING,
            name="agente_product_matching",
            response_format=ProductosMGA,
        )
        return product_matching_agent_builder

    def _product_matcher(self, state: ProductMatchingState, config: RunnableConfig):

        agent = self._product_matching_agent(config)

        producto_sugerido = state.get("producto_sugerido")
        human_msg = HumanMessage(
                content = f"Por favor procede con la identificación del producto de la MGA de acuerdo al catalogo que se encuentra vectorizado para tu consulta. Considera la siguiente información de entrada:\n\n1. Producto sugerido:\n{producto_sugerido.producto} \n\n2. Descripción del producto sugerido:\n{producto_sugerido.descripcion} \n\n3. Objetivo general del proyecto:\n{state.get("objetivo_general")} \n\n4. Objetivo específico del proyecto:\n{state.get("objetivo_especifico")}")

        productos_mga = agent.invoke({"messages": human_msg}, config)

        df_acts = _buscar_actividades_edt(productos_mga.descripcion)
        acts = _df_to_pydantic_list(df_acts)
        
        item_value_chain = ValueChainItem(
            objetivo_especifico=state.get("objetivo_general"),
            producto=productos_mga.producto,
            indicador_verificacion=productos_mga.indicador_verificacion,
            meta=None,
            actividades=[act.actividad for act in acts],
        )
        
        return Command(
            update={
                "productos_mga": [productos_mga.productos_mga],
                "value_chain": [ValueChain(items=[item_value_chain])]
                },
            goto="activity_selection",
        )

    # ─────────── 3) activity_selection (NUEVO) ─────────────────
    def _activity_selection(self, state: ValueChainState, cfg: RunnableConfig):

        actividades_pyd: List[ActivityEDT] = []
        value_chain_items: List[ValueChainItem] = []

        objetivos = state.objetivos_especificos or []
        if not objetivos:
            raise ValueError("No hay objetivos específicos en el estado.")

        for prod in state.productos_mga:
            df_acts = _buscar_actividades_edt(prod.descripcion)
            acts = _df_to_pydantic_list(df_acts)
            actividades_pyd.extend(acts)

            actividades_nombres = [a.actividad for a in acts]
            for obj in objetivos:
                value_chain_items.append(
                    ValueChainItem(
                        objetivo_especifico=obj,
                        producto=prod.producto,
                        indicador_verificacion=prod.medido_a_traves_de,
                        meta=None,
                        actividades=actividades_nombres,
                    )
                )

        return Command(
            update={
                "actividades_edt": ActivitiesEDT(actividades=actividades_pyd),
                "cadena_valor": ValueChain(items=value_chain_items),
            },
            goto="edt_builder",
        )

    # ─────────── 5) build graph ────────────────────────────────
    def _build_value_chain(self):
        g = StateGraph(ValueChainState)
        g.set_entry_point("generate_products")
        g.add_node("generate_products", self._generate_products)
        g.add_node("product_matcher",    self._product_matcher)
        return g.compile()

    # ─────────── 6) run ────────────────────────────────────────
    def run(self, state: ValueChainState, cfg) -> Command[Literal["metodologia_proyecto"]]:
        graph = self._build_value_chain()
        result = graph.invoke(state, cfg)
        return Command(
            update={
                "messages":       result.get("messages", []) + [HumanMessage(content="Diseño de proyecto completado.")],
                "edt_seleccionada": result.edt_seleccionada,
                "marco_logico":     result.marco_logico,
                "cadena_valor":     result.cadena_valor,
            },
            goto="metodologia_proyecto",
        )

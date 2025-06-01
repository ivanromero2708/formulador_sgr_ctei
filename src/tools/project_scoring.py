import os
import json
import requests
from typing import List
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langsmith import traceable
from pydantic import BaseModel, Field

load_dotenv()

class ProjectScore(BaseModel):
    score: float = Field(description="Score between 0 and 100")

@tool(
    description=(
        "Recibe un borrador de proyecto y los criterios de evaluación del TDR, "
        "evalúa cada criterio y devuelve una puntuación global (0–100)."
    )
)
@traceable
def project_scoring_tool(borrador_concepto: str, criterios_evaluacion_proyectos_tdr: str):
    """
    Takes the project information and the evaluation criteria from the TDR and assess the project according those metrics.
    Returns a float value between 0 and 100.
    """
    llm_model = ChatOpenAI(model = "o4-mini", reasoning_effort = "medium")  
    structured_llm = llm_model.with_structured_output(ProjectScore)
    
    prompt = f"""
    Eres un evaluador experto de proyectos científicos. 
    Analiza el siguiente borrador y evalúalo según estos criterios:

    Borrador de proyecto:
    <borrador_concepto>{borrador_concepto}</borrador_concepto>

    Criterios de evaluación:
    <criterios_evaluacion_proyectos_tdr>{criterios_evaluacion_proyectos_tdr}</criterios_evaluacion_proyectos_tdr>

    Devuélveme SOLO un JSON con la clave "score" y un valor entre 0 y 100, sin ningún comentario extra.
    """
    
    response = structured_llm.invoke(prompt)
    
    return response.score
    
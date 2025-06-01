import os
import json
import requests
from typing import List
from langchain_core.tools import tool
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

@tool(description="Utiliza la API de Serper.dev para recuperar una lista de enlaces de artículos de investigación basados en una consulta de búsqueda. Retorna una lista de URLs. Si ocurre un error o se agota el tiempo, retorna una lista vacía.")
@traceable
def serper_dev_search_tool(query: str, max_results: int = 5) -> List[str]:
    """
    Utiliza la API de Serper.dev para recuperar una lista de enlaces de artículos de investigación
    basados en una consulta de búsqueda. Retorna una lista de URLs.
    Si ocurre un error o se agota el tiempo, retorna una lista vacía.
    """
    SERPER_URL = "https://google.serper.dev/scholar"
    
    # The SERPER_API_KEY environment variable must be set
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY environment variable not set.")
    
    # Prepare the request payload. 
    # You can add or remove fields (e.g. gl, hl, autocorrect) as needed.
    payload = {
        "q": query,
        "num": max_results,    # How many organic results to fetch
        "type": "search",      # Required by Serper for standard web search
        "autocorrect": True,   # Optional
        "gl": "us",            # Optional: geolocation (country)
        "hl": "en"             # Optional: language
    }
    
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            SERPER_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=10.0
        )
        response.raise_for_status()  # Raise an HTTPError if 4xx/5xx
        results = response.json()
        
        # Serper's response uses the "organic" key for search results
        organic_results = results.get("organic", [])
        
        # Collect the top links up to max_results
        links = []
        for result in organic_results[:max_results]:
            link = result.get("link")
            if link:
                links.append(link)
        
        return links
    
    except requests.exceptions.RequestException as e:
        print(f"Error making request to Serper API: {e}")
        return []

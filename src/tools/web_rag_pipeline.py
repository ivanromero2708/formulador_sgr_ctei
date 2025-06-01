import os
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

def clean_text(text: str) -> str:
    """Utilidad para limpiar espacios adicionales y saltos de línea."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()

class WebRAGPipelineToolInput(BaseModel):
    website_url: str = Field(
        ..., description="La URL del sitio web del cual obtener el contenido."
    )
    search_query: str = Field(
        ..., description="Consulta de búsqueda que se usará para recuperar fragmentos relevantes del documento."
    )

@tool(description="""Esta herramienta realiza los siguientes pasos:
    1) Obtiene el contenido del sitio web desde la URL proporcionada.
       - Utiliza una solicitud HEAD para determinar si el contenido es un PDF o HTML.
       - Si es PDF, carga el contenido usando PyPDFLoader.
       - Si es HTML, carga el contenido usando requests y BeautifulSoup.
    2) Divide el contenido cargado en fragmentos más pequeños.
    3) Crea un vector store en memoria a partir de los fragmentos utilizando OpenAIEmbeddings.
    4) Usa búsqueda de máxima relevancia marginal con la consulta de búsqueda proporcionada para recuperar los fragmentos más relevantes.

    Retorna:
      Un diccionario con una clave "documents" que contiene una cadena con el contexto concatenado de los mejores resultados.""")
def web_rag_pipeline_tool(website_url: str, search_query: str) -> dict:
    """
    Esta herramienta realiza los siguientes pasos:
      1) Obtiene el contenido del sitio web desde la URL proporcionada.
         - Utiliza una solicitud HEAD para determinar si el contenido es un PDF o HTML.
         - Si es PDF, carga el contenido usando PyPDFLoader.
         - Si es HTML, carga el contenido usando requests y BeautifulSoup.
      2) Divide el contenido cargado en fragmentos más pequeños.
      3) Crea un vector store en memoria a partir de los fragmentos utilizando OpenAIEmbeddings.
      4) Usa búsqueda de máxima relevancia marginal con la consulta de búsqueda proporcionada para recuperar los fragmentos más relevantes.
    
    Retorna:
      Un diccionario con una clave "documents" que contiene una cadena con el contexto concatenado de los mejores resultados.
    """

    url = website_url

    # --- Step 1: Fetch URL content ---
    def fetch_url(url: str) -> Optional[str]:
        try:
            head_response = requests.head(url, allow_redirects=True, timeout=10)
            content_type = head_response.headers.get("Content-Type", "").lower()
        except Exception as e:
            print(f"HEAD request failed for {url}: {e}")
            return None

        # If the content is PDF, use PyPDFLoader.
        if "application/pdf" in content_type or "pdf" in url.lower():
            try:
                loader = PyPDFLoader(url)
                docs = loader.lazy_load()
                if docs:
                    joined_text = "\n\n".join(doc.page_content for doc in docs)
                    return clean_text(joined_text)
                else:
                    return None
            except Exception as e:
                print(f"Error loading PDF from {url}: {e}")
                return None
        else:
            # Otherwise, treat as HTML.
            try:
                response = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                })
                response.encoding = response.apparent_encoding
                parsed = BeautifulSoup(response.text, "html.parser")
                text = parsed.get_text(" ")
                return clean_text(text)
            except Exception as e:
                print(f"Error loading HTML from {url}: {e}")
                return None

    content = fetch_url(url)
    if not content:
        print("Failed to load content from the URL.")
        return "Failed to load content from the URL."

    # --- Step 2: Split the content into chunks ---
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " "]
    )
    doc = Document(page_content=content, metadata={"source": url})
    doc_splits = splitter.split_documents([doc])
    if not doc_splits:
        print("Document splitting returned no chunks.")
        return "Document splitting returned no chunks."

    # --- Step 3: Create vector store from the chunks ---
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = InMemoryVectorStore.from_documents(
        embedding=embeddings,
        documents=doc_splits
    )

    # --- Step 4: Perform max marginal relevance search ---
    try:
        final_docs = vector_store.max_marginal_relevance_search(
            search_query, k=7
        )
        document_context = "\n\n".join(
            f"Source: {doc.metadata.get('source', 'No URL available')}\nContent: {doc.page_content}"
            for doc in final_docs
        )
    except Exception as e:
        print(f"Error during vector search: {e}")
        return f"Error during vector search: {e}"

    return document_context

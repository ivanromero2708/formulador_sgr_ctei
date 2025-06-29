import os
import re
import base64
import requests
from bs4 import BeautifulSoup
from typing import Optional, List
from pydantic import BaseModel, Field
from mistralai import Mistral                           # 🔸 CORREGIDO A LA NUEVA API
from langchain_core.tools import tool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document


# ---------- utilidades ---------- #
def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+",  "\n", text)
    return text.strip()


class WebRAGPipelineToolInput(BaseModel):
    website_url: str = Field(..., description="URL a procesar (PDF o HTML)")
    search_query: str = Field(..., description="Consulta para recuperar fragmentos relevantes")


# ---------- función principal ---------- #
@tool(
    description="""
    Descarga el contenido (PDF o HTML) de una URL, lo trocea, crea un vector-store en memoria
    y devuelve los fragmentos más relevantes según la consulta.
    """
)
def web_rag_pipeline_tool(website_url: str, search_query: str) -> dict:   # <- tip: Pydantic input si lo prefieres
    # --- 1) Descargar -------------------------------------------------- #
    def fetch_url(url: str) -> Optional[str]:
        try:
            head = requests.head(url, allow_redirects=True, timeout=10)
            ctype = head.headers.get("Content-Type", "").lower()
        except Exception as e:
            print(f"[HEAD] {url} → {e}")
            return None

        # ----- PDF  →  OCR Mistral ------------------------------------- #
        if "application/pdf" in ctype or url.lower().endswith(".pdf"):
            api_key = os.getenv("MISTRAL_API_KEY")
            if not api_key:
                raise RuntimeError("Define la variable de entorno MISTRAL_API_KEY")

            try:
                client = Mistral(api_key=api_key)

                # Descargar el contenido del PDF primero
                pdf_response = requests.get(url, timeout=30, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                })
                pdf_response.raise_for_status() # Asegura que la descarga fue exitosa

                # Codificar en Base64
                base64_pdf = base64.b64encode(pdf_response.content).decode('utf-8')
                data_url = f"data:application/pdf;base64,{base64_pdf}"

                # Enviar el contenido Base64 a Mistral
                ocr_resp = client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url", # Sigue siendo 'document_url' para data URIs
                        "document_url": data_url
                    },
                    include_image_base64=True
                )

                # La respuesta contiene un array de páginas con `.markdown`
                # La respuesta es un objeto, no un dict. Se accede con `.`
                pages_md: List[str] = [p.markdown for p in ocr_resp.pages]
                return clean_text("\n\n".join(pages_md))

            except Exception as e:
                print(f"[Mistral OCR] {url} → {e}")
                return None

        # ----- HTML ----------------------------------------------------- #
        try:
            res = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            })
            res.encoding = res.apparent_encoding
            soup = BeautifulSoup(res.text, "html.parser")
            return clean_text(soup.get_text(" "))
        except Exception as e:
            print(f"[HTML] {url} → {e}")
            return None

    content = fetch_url(website_url)
    if not content:
        return {"error": "No se pudo obtener contenido de la URL"}

    # --- 2) Split ------------------------------------------------------- #
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n\n", "\n", " "]
    )
    doc_splits = splitter.split_documents([Document(page_content=content,
                                                    metadata={"source": website_url})])

    # --- 3) Vector store ------------------------------------------------ #
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", chunk_size=256)
    vectordb  = InMemoryVectorStore.from_documents(doc_splits, embeddings)

    # --- 4) Recuperación MMR ------------------------------------------- #
    try:
        top_docs = vectordb.max_marginal_relevance_search(search_query, k=10)
        joined    = "\n\n".join(
            f"Source: {d.metadata.get('source', '')}\nContent: {d.page_content}"
            for d in top_docs
        )
        return {"documents": joined}
    except Exception as e:
        return {"error": f"Vector search failed: {e}"}

# src/tools/catalogo_mga.py
from pathlib import Path
from typing import List, Dict, Any

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai      import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool

# ───── Config común ───────────────────────────────────────────────────────────
HF_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"
OA_MODEL   = "text-embedding-3-small"
HF_INDEX   = Path("src/databases/faiss_ctei_hf")        # ya existente
OA_INDEX   = Path("src/databases/faiss_ctei_openai")    # creado con script
COLS_KEEP  = [  # las 24 columnas solicitadas
    "Sector", "Nombre del Sector", "Código del Programa", "Nombre del Programa",
    "Código del Producto", "Producto", "Descripción", "Medido a través de",
    "Código del Indicador de Producto", "Indicador de Producto", "Unidad de medida",
    "Indicador Principal", "Es Nacional", "Es Territorial",
    "Objetivos de Desarrollo Sostenible - ODS", "Meta ODS",
    "Tipología General", "Tipología D", "Tipología E",
    "Tipología A", "Tipología B", "Tipología C",
    "Tiene EDT", "EDT",
]

# ───── Cargadores perezosos (se instancian solo 1 vez por backend) ────────────
_CACHE = {}

def _load_backend(backend: str):
    """
    backend = 'openai' | 'hf'
    """
    if backend in _CACHE:
        return _CACHE[backend]

    if backend == "openai":
        emb   = OpenAIEmbeddings(model=OA_MODEL)
        store = FAISS.load_local(str(OA_INDEX), emb, allow_dangerous_deserialization=True)
    elif backend == "hf":
        emb   = HuggingFaceEmbeddings(model_name=HF_MODEL)
        store = FAISS.load_local(str(HF_INDEX), emb, allow_dangerous_deserialization=True)
    else:
        raise ValueError("backend debe ser 'openai' o 'hf'")

    _CACHE[backend] = store.as_retriever(search_kwargs={"k": 5})
    return _CACHE[backend]

# ───── Tool ───────────────────────────────────────────────────────────────────
@tool("vec_retriever_ctei", return_direct=False)
def vec_retriever_ctei(query: str,
                       k: int = 5,
                       backend: str = "openai") -> List[Dict[str, Any]]:
    """
    Recupera hasta *k* productos del catálogo CTeI.
    Parámetros
    ----------
    query    : texto de búsqueda
    k        : número de registros (default 5)
    backend  : 'openai' (text-embedding-3-small)  |  'hf' (MiniLM-L6)
    """
    retriever = _load_backend(backend)
    retriever.search_kwargs["k"] = k
    docs = retriever.invoke(query)                      # sin warning

    return [
        {
            "content": d.page_content,
            "fields" : {c: d.metadata.get(c, "") for c in COLS_KEEP},
            "backend": backend,
        }
        for d in docs
    ]

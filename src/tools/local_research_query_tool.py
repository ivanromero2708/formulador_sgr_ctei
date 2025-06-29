from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_core.tools import tool

@tool
def local_research_query_tool(query: str, persist_path: str) -> str:
    """
    Consulta de documentos locales usando un retriever.
        
    Args:
        query (str): La consulta a hacer sobre la documentación

    Returns:
        str: Un str de los documentos recuperados
    """
    
    if persist_path == "":
        return "There is no provided documentation to search in."
    
    retriever = SKLearnVectorStore(
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        persist_path=persist_path,
        serializer="parquet").as_retriever(search_type="mmr", search_kwargs={"k": 10}
    )

    relevant_docs = retriever.invoke(query)
    print(f"Retrieved {len(relevant_docs)} relevant documents")
    formatted_context = "\n\n".join([f"==DOCUMENT {i+1}==\n{doc.page_content}" for i, doc in enumerate(relevant_docs)])
    return formatted_context

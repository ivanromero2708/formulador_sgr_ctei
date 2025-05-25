import os
from typing import Literal, List
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, Send
from langsmith import traceable
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from src.graph.state import FormuladorCTeIAgent
from src.config.configuration import SECCIONES_TDR
from src.prompts.prompt_process_init import USER_PROMPT_TEMPLATE

class TDRVectorStore:
    def __init__(self):
        pass

    @traceable
    def load_document(self, file_path: str) -> List[Document]:
        """Loads document content from the given file path."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path=file_path)
        elif ext == ".docx":
            loader = UnstructuredWordDocumentLoader(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Please provide a PDF or DOCX file.")
        
        docs = loader.load()
        if not docs:
            raise ValueError(f"No content could be extracted from {file_path}")
        
        return docs

    @traceable
    def split_documents(self, docs):
        """
        Divide el texto en chunks para crear embeddings.
        :param docs: Documentos (chunks).
        :return: Lista de documentos (chunks).
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        return splitter.split_documents(docs)
    
    @traceable
    def create_vectorstore(self, splits):
        """
        Crea y persiste un vector store a partir de los chunks de la transcripción.
        :param splits: Lista de chunks.
        :return: vectorstore y la ruta de persistencia.
        """
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Usar Path para generar el directorio y convertirlo a POSIX (con "/" como separador)
        persist_path = Path(os.getcwd()) / "temp_uploads" / "tdr_vectorstore.parquet"
        persist_path = persist_path.as_posix()  # Se convierte a formato POSIX ("/")

        vectorstore = SKLearnVectorStore.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_path=persist_path,
            serializer="parquet",
        )

        vectorstore.persist()
        return vectorstore, persist_path
        
    @traceable
    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["coordinador_general", "tdr_parsing_agent"]]:
        """
        Parses the TDR document to extract key information and updates the state.
        """
        print("---EJECUTANDO NODO: TDRParsing---")
        tdr_file_path = state.get("tdr_document_path")

        
        if not tdr_file_path or not os.path.exists(tdr_file_path):
            error_message = f"Ruta del documento TDR ('{tdr_file_path}') es inválida o no existe en el estado actual."
            print(error_message)
            return Command(
                update={
                    "messages": state.get("messages", []) + [AIMessage(content=error_message, name="TDRVectorStore")]
                },
                goto="coordinador_general",
            )

        try:
            tdr_documents = self.load_document(tdr_file_path)
            splits = self.split_documents(tdr_documents)
            vectorstore, persist_path = self.create_vectorstore(splits)
            
            goto = [
                    Send(
                        "tdr_parsing_agent",
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": USER_PROMPT_TEMPLATE.format(
                                        seccion_tdr=seccion_tdr,
                                        persist_path=persist_path,
                                        definicion=SECCIONES_TDR[seccion_tdr]["definicion"]
                                    )
                                }
                            ],
                            "seccion_tdr": seccion_tdr,
                            "persist_path": persist_path,
                        }
                    )
                for seccion_tdr in SECCIONES_TDR.keys()
            ]

            return Command(
                goto=goto,
            )
            
        except ValueError as e:
            error_message = f"Error cargando el documento TDR: {str(e)}"
            print(error_message)
            return Command(
                update={
                    "messages": state.get("messages", []) + [AIMessage(content=error_message, name="TDRVectorStore")]
                },
                goto="coordinador_general",
            )

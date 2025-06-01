from src.llms.llm import create_llm_model
from src.prompts.template import apply_prompt_template
# from src.utils.json_utils import repair_json_output # Eliminado con trustcall
from src.config.configuration import MultiAgentConfiguration
from src.graph.state import (
    FormuladorCTeIAgent,
    CoordinadorGeneralOutput,
)
from trustcall import create_extractor # Añadido para trustcall

from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, BaseMessage # BaseMessage para el tipado de CoordinadorGeneralOutput.messages

from typing import Literal, Sequence

class CoordinadorGeneral:
    def __init__(self):
        pass

    def run(self, state: FormuladorCTeIAgent, config: RunnableConfig) -> Command[Literal["__end__", "tdr_vectorstore"]]:
        # Inicialización de la configuración del agente
        agent_configuration = MultiAgentConfiguration.from_runnable_config(config)
        llm_config_name = agent_configuration.gpt4omini

        # Obtener la instancia del LLM
        llm_instance = create_llm_model(llm_config_name)

        # Crear el extractor de trustcall
        extractor = create_extractor(
            llm_instance,
            tools=[CoordinadorGeneralOutput],
            tool_choice=CoordinadorGeneralOutput.__name__
        )

        # Formateo de los mensajes de entrada para el LLM
        input_messages = apply_prompt_template("coordinador_general", state)

        # Invocación del extractor de trustcall
        trustcall_input = {"messages": input_messages}
        extraction_result = extractor.invoke(trustcall_input)

        # Procesar la respuesta de trustcall
        if not extraction_result["responses"]:
            error_content = "Error: CoordinadorGeneral no pudo extraer la información necesaria usando trustcall."
            current_error_messages = state.get("error_messages", [])
            if isinstance(current_error_messages, list):
                updated_error_messages = current_error_messages + [error_content]
            else:
                updated_error_messages = [error_content]

            return Command(
                update={
                    "messages": [AIMessage(content=error_content, name="coordinador_general_error")],
                    "error_messages": updated_error_messages,
                },
                goto="__end__" 
            )

        parsed_output: CoordinadorGeneralOutput = extraction_result["responses"][0]

        # El contenido para el AIMessage en el estado provendrá del campo 'messages' dentro de parsed_output
        response_content_for_aimessage = ""
        if parsed_output.messages and isinstance(parsed_output.messages, Sequence) and len(parsed_output.messages) > 0:
            # Asegurarse de que el último mensaje tenga contenido y sea un string
            last_message_in_output = parsed_output.messages[-1]
            if hasattr(last_message_in_output, 'content') and isinstance(last_message_in_output.content, str):
                response_content_for_aimessage = last_message_in_output.content
            elif isinstance(last_message_in_output, str): # Si el mensaje es directamente un string
                 response_content_for_aimessage = last_message_in_output
        
        if not response_content_for_aimessage:
            # Fallback si el LLM no populó el campo 'messages' dentro de CoordinadorGeneralOutput como se esperaba.
            # Usar una representación de la tool call de trustcall como contenido.
            if extraction_result["messages"] and extraction_result["messages"][0].tool_calls:
                 response_content_for_aimessage = f"Tool call to {CoordinadorGeneralOutput.__name__} with args: {extraction_result['messages'][0].tool_calls[0]['args']}"
            else:
                 response_content_for_aimessage = "CoordinadorGeneral procesó la entrada."

        # Determinar los nodos de destino
        if parsed_output.hand_off_to_planner:
            goto: Sequence[str] = ["tdr_vectorstore"]
        else:
            goto = "__end__"

        # Devolver el comando con la actualización de estado y nodos de destino
        return Command(
            update={
                "messages": [
                    AIMessage(
                        content=response_content_for_aimessage,
                        name="coordinador_general",
                    )
                ],
                "tdr_document_path": parsed_output.tdr_document_path,
                "departamento": parsed_output.departamento,
                "additional_documents_paths": parsed_output.additional_documents_paths,
                "entidad_proponente_usuario": parsed_output.entidad_proponente_usuario,
                "alianzas_usuario": parsed_output.alianzas_usuario,
                "demanda_territorial_seleccionada_usuario": parsed_output.demanda_territorial_seleccionada_usuario,
                "idea_base_proyecto_usuario": parsed_output.idea_base_proyecto_usuario,
                "duracion_proyecto_usuario": parsed_output.duracion_proyecto_usuario,
                "presupuesto_estimado_usuario": parsed_output.presupuesto_estimado_usuario,
            },
            goto=goto
        )

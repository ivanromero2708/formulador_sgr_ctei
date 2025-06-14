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
        llm_config_name = agent_configuration.gpt41mini

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
                    "messages": [AIMessage(content=error_content, name="coordinador_general")],
                    "error_messages": updated_error_messages,
                },
                goto="__end__" 
            )

        parsed_output: CoordinadorGeneralOutput = extraction_result["responses"][0]

        # El contenido para el AIMessage en el estado provendrá del campo 'messages' dentro de parsed_output
        response_content_for_aimessage = parsed_output.messages[-1].content

        # Determinar los nodos de destino
        if parsed_output.hand_off_to_planner:
            goto: Sequence[str] = ["tdr_vectorstore"]
        else:
            goto = "__end__"

        # Construct the update payload conditionally to avoid overwriting existing state with None
        update_payload = {
            "messages": [
                AIMessage(
                    content=response_content_for_aimessage,
                    name="coordinador_general",
                )
            ]
        }

        # Define which attributes from parsed_output should be considered for updating the state.
        # These correspond to the fields in CoordinadorGeneralOutput that map to FormuladorCTeIAgent state.
        fields_to_potentially_update = [
            "tdr_document_path", "departamento", "plan_desarrollo_nacional",
            "plan_desarrollo_departamental", "additional_documents_paths",
            "entidad_proponente_usuario", "alianzas_usuario",
            "demanda_territorial_seleccionada_usuario", "idea_base_proyecto_usuario",
            "duracion_proyecto_usuario", "presupuesto_estimado_usuario"
        ]

        for field_name in fields_to_potentially_update:
            if hasattr(parsed_output, field_name):
                value = getattr(parsed_output, field_name)
                # Only update the state if the parsed output has a non-None value for the field.
                # This prevents accidental clearing of existing state data.
                # For list fields with default_factory=list in CoordinadorGeneralOutput (like additional_documents_paths),
                # if the LLM doesn't provide them, `value` will be `[]`. `[] is not None` is true, so the state will be updated to `[]`.
                # This is generally the expected behavior: if the model is asked to extract a list and returns/defaults to an empty list, the state reflects that.
                # For Optional[List[...]] fields (like alianzas_usuario), if the LLM doesn't provide them, `value` will be `None`, and the state won't be updated.
                if value is not None:
                    update_payload[field_name] = value

        # Devolver el comando con la actualización de estado y nodos de destino
        return Command(
            update=update_payload,
            goto=goto
        )

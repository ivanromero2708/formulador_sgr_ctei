from ..state import FormuladorCTeIAgent, DocumentoTecnicoCompleto, DocumentoTecnicoSeccion

class TechnicalDocumentWriting:
    def __init__(self):
        # Initialization for TechnicalDocumentWriting node
        pass

    def run(self, state: FormuladorCTeIAgent) -> FormuladorCTeIAgent:
        print("---EJECUTANDO NODO: TechnicalDocumentWriting---")
        # This node populates the technical document based on the selected project,
        # logical framework, budget, TDR templates, and other relevant information.

        # proyecto_seleccionado = state.get('proyecto_seleccionado_detalle')
        # marco_logico = state.get('marco_logico_final')
        # presupuesto = state.get('presupuesto_detallado_final')
        # plantillas_tdr = state.get('plantillas_oficiales_tdr')
        # entidad_proponente = state.get('entidad_proponente_usuario')
        # equipo_tecnico = state.get('equipo_tecnico_clave_usuario')

        # if proyecto_seleccionado and marco_logico and presupuesto and plantillas_tdr:
            # documento = DocumentoTecnicoCompleto(
            #     secciones=[
            #         DocumentoTecnicoSeccion(numero_seccion="1.0", titulo_seccion="Resumen Ejecutivo", contenido_generado="Contenido del resumen..."),
            #         DocumentoTecnicoSeccion(numero_seccion="2.0", titulo_seccion="Planteamiento del Problema", contenido_generado=proyecto_seleccionado.problema_abordado)
            #     ]
            # )
            # if plantillas_tdr.estructura_documento_tecnico:
            #     print(f"Usando estructura de {len(plantillas_tdr.estructura_documento_tecnico)} secciones del TDR.")
            #     # Aquí se iteraría sobre plantillas_tdr.estructura_documento_tecnico
            #     # y se generararía el contenido para cada sección usando LLMs.

            # state['documento_tecnico_final'] = documento
            # print("Documento técnico redactado.")
        # else:
        #     error_msg = "Faltan datos para la redacción del documento técnico."
        #     state['error_messages'] = (state.get('error_messages', []) + [error_msg])
        #     print(f"Error: {error_msg}")

        state['current_node_execution'] = self.__class__.__name__
        return state

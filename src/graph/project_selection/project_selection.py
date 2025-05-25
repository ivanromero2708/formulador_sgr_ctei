from ..state import FormuladorCTeIAgent

class ProjectSelection:
    def __init__(self):
        # Initialization for ProjectSelection node
        pass

    def run(self, state: FormuladorCTeIAgent) -> FormuladorCTeIAgent:
        print("---EJECUTANDO NODO: ProjectSelection---")
        # This node would typically involve user interaction to select one
        # of the generated project concepts (from state.conceptos_proyecto_generados).
        # For now, it might select the first one by default or require external input.

        # conceptos = state.get('conceptos_proyecto_generados', [])
        # if conceptos:
        #     selected_id = conceptos[0].id_concepto # Placeholder: select the first
        #     state['concepto_proyecto_seleccionado_id'] = selected_id
        #     state['proyecto_seleccionado_detalle'] = conceptos[0]
        #     print(f"Proyecto seleccionado (ID): {selected_id}")
        # else:
        #     error_msg = "No hay conceptos de proyecto generados para seleccionar."
        #     state['error_messages'] = (state.get('error_messages', []) + [error_msg])
        #     print(f"Error: {error_msg}")

        state['current_node_execution'] = self.__class__.__name__
        return state

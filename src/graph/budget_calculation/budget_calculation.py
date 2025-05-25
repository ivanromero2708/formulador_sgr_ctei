from ..state import FormuladorCTeIAgent, PresupuestoDetallado, PresupuestoRubro

class BudgetCalculation:
    def __init__(self):
        # Initialization for BudgetCalculation node
        pass

    def run(self, state: FormuladorCTeIAgent) -> FormuladorCTeIAgent:
        print("---EJECUTANDO NODO: BudgetCalculation---")
        # This node uses the selected project, TDR financial constraints,
        # user's estimated budget, and any justified singular costs
        # to calculate a detailed budget.

        # proyecto_seleccionado = state.get('proyecto_seleccionado_detalle')
        # restricciones_financieras = state.get('restricciones_financieras_tdr')
        # presupuesto_usuario = state.get('presupuesto_estimado_usuario')
        # justificaciones_costos = state.get('justificaciones_costos_usuario')
        # actividades_marco_logico = state.get('marco_logico_final').actividades_por_componente if state.get('marco_logico_final') else None

        # if proyecto_seleccionado and restricciones_financieras and presupuesto_usuario:
            # presupuesto = PresupuestoDetallado(
            #     rubros=[
            #         PresupuestoRubro(descripcion="Ejemplo Rubro Personal", valor_total_sgr=1000000),
            #         PresupuestoRubro(descripcion="Ejemplo Rubro Equipos", valor_total_sgr=500000)
            #     ],
            #     total_sgr=1500000
            # )
            # state['presupuesto_detallado_final'] = presupuesto
            # print("Presupuesto detallado calculado.")
        # else:
        #     error_msg = "Faltan datos para el cálculo del presupuesto."
        #     state['error_messages'] = (state.get('error_messages', []) + [error_msg])
        #     print(f"Error: {error_msg}")

        state['current_node_execution'] = self.__class__.__name__
        return state

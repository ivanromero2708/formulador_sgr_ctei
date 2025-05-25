# ---------------------------------------------------------------------------
# STREAMLIT HYBRID CHAT + INTERRUPT APP
# ---------------------------------------------------------------------------
import os, uuid, asyncio, tempfile
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

# ▸▸▸  1.  ⎯⎯⎯  PROJECT–SPECIFIC GRAPH  ⎯⎯⎯
#
#   ⚠️  CHANGE THESE IMPORTS to your own workflow graph & state classes
#   -----------------------------------------------------------------
from src.graph.project_formulation_graph import project_formulation_graph          # ← your graph
from src.state import FormulationGraphState                                        # ← your state dataclass

# ▸▸▸  2.  ⎯⎯⎯   STREAMLIT PAGE  ⎯⎯⎯
st.set_page_config(page_title="Formulador de Proyectos CTeI", layout="wide")
st.title("💡 Formulador de Proyectos CTeI")

# ▸▸▸  3.  ⎯⎯⎯  SESSION VARIABLES  ⎯⎯⎯
if "thread_info"     not in st.session_state: st.session_state.thread_info   = {"configurable": {"thread_id": str(uuid.uuid4())}}
if "messages"        not in st.session_state: st.session_state.messages      = [AIMessage(content="Hola 👋 — cuéntame sobre tu proyecto y recopilaré la información necesaria.")]
if "mode"            not in st.session_state: st.session_state.mode          = "collecting_input"  # other states: running_graph, waiting_feedback, finished
if "structured_in"   not in st.session_state: st.session_state.structured_in = {}                  # will hold the answers
if "graph_snapshot"  not in st.session_state: st.session_state.graph_snapshot= None                 # latest interrupt payload

# Simple helper to show chat history
def replay_history():
    for m in st.session_state.messages:
        role = "assistant" if isinstance(m, AIMessage) else "user"
        st.chat_message(role).write(m.content)

# ---------------------------------------------------------------------------
# 4. COLLECT STRUCTURED INPUTS IN CONVERSATION
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = [
    ("nombre_proyecto",         "¿Cuál es el nombre tentativo del proyecto?"),
    ("sector",                  "¿A qué sector pertenece?"),
    ("problema_oportunidad",    "Describe brevemente el problema u oportunidad."),
    ("objetivo_general",        "¿Cuál es el objetivo general?"),
    ("monto_estimado",          "¿Monto estimado (COP)?"),
]

def next_missing_field():
    for key, _ in REQUIRED_FIELDS:
        if key not in st.session_state.structured_in:
            return key
    return None

# ---------------------------------------------------------------------------
# 5. MAIN EVENT LOOP
# ---------------------------------------------------------------------------
replay_history()

if prompt := st.chat_input():
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").write(prompt)

    # ──────────────────────────────────────────────────────────────
    #   MODE 1: collecting structured data
    # ──────────────────────────────────────────────────────────────
    if st.session_state.mode == "collecting_input":

        # save answer to the current expected field
        current_key = next_missing_field()
        if current_key:
            st.session_state.structured_in[current_key] = prompt

        missing = next_missing_field()
        if missing:
            question = dict(REQUIRED_FIELDS)[missing]
            st.session_state.messages.append(AIMessage(content=question))
            st.chat_message("assistant").write(question)
        else:
            # we have everything –> launch the graph until first interrupt
            st.session_state.mode = "running_graph"
            st.rerun()

    # ──────────────────────────────────────────────────────────────
    #   MODE 2: awaiting feedback buttons
    # ──────────────────────────────────────────────────────────────
    elif st.session_state.mode == "waiting_feedback":
        # store the choice; resume graph
        human_response = {"feedback_decision": prompt}  # simple scheme; adapt if you pass extra details
        st.session_state.mode = "running_graph"
        st.session_state.resume_payload = Command(resume=human_response)
        st.rerun()

# ---------------------------------------------------------------------------
# 6.  RUN / RESUME THE GRAPH WHEN NEEDED
# ---------------------------------------------------------------------------
if st.session_state.mode == "running_graph":
    async def run_until_interrupt(initial=None, resume=None):
        async for ev in project_formulation_graph.astream(
            initial or resume,
            st.session_state.thread_info,
            stream_mode="updates",
        ):
            last = ev
        return last["__interrupt__"]  # type: ignore

    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)

    if "resume_payload" in st.session_state:
        interrupt_payload = loop.run_until_complete(
            run_until_interrupt(resume=st.session_state.resume_payload)
        )
        del st.session_state.resume_payload
    else:
        # build initial graph state from collected fields
        init_state = FormulationGraphState(
            **st.session_state.structured_in,          # unpack structured input
            optional_files=[],                         # add anything else you need
        )
        interrupt_payload = loop.run_until_complete(
            run_until_interrupt(initial=init_state)
        )

    # cache interrupt payload
    st.session_state.graph_snapshot = interrupt_payload
    st.session_state.mode = "waiting_feedback"
    st.rerun()

# ---------------------------------------------------------------------------
# 7.  PRESENT ALTERNATIVES & BUTTONS
# ---------------------------------------------------------------------------
if st.session_state.mode == "waiting_feedback" and st.session_state.graph_snapshot:
    intr = st.session_state.graph_snapshot[0].value
    alternatives = intr.get("alternatives", [])  # <-- adapt to your graph’s state key

    with st.chat_message("assistant"):
        st.write("### He encontrado las siguientes alternativas de proyecto:")
        for i, alt in enumerate(alternatives):
            st.markdown(f"**{i+1}.** {alt['titulo']}  \n> {alt['resumen']}")

        st.divider()
        # Build buttons dynamically
        cols = st.columns(len(alternatives))
        for i, col in enumerate(cols):
            if col.button(f"Elegir {i+1}", key=f"alt_{i}"):
                # store selection & resume
                st.session_state.messages.append(HumanMessage(content=f"Elegí alternativa {i+1}"))
                st.session_state.messages.append(AIMessage(content=f"Perfecto, continúo con la alternativa {i+1}."))
                st.session_state.mode = "running_graph"
                st.session_state.resume_payload = Command(
                    resume={"feedback_decision": "chosen_alternative", "index": i}
                )
                st.rerun()

    # optional cancel / reset
    if st.button("⟲ Reiniciar"):
        st.session_state.clear(); st.rerun()

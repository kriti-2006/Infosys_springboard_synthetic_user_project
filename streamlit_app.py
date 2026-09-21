"""
Minimal Streamlit UI for the Synthetic Persona Research Platform.

This is intentionally small: it reuses the existing `run_pipeline()` and
`generate_pdf_report()` logic unchanged, and adds only what's needed to:

1. Run the existing persona -> survey -> response -> insight pipeline from
   a form instead of the hardcoded main.py demo.
2. Display the generated personas as visual cards (name, age, occupation,
   personality traits, behavioral patterns, psychological profile, summary)
   — the requirement this UI exists to satisfy.
3. Let the user pick one of the generated personas and run the REQUIRED
   Interview Mode: a direct, memory-carrying conversation with that persona
   (agents.interview_agent.start_persona_interview / PersonaInterviewSession).

The existing CLI (`python main.py`) keeps working unchanged.

Run with:
    streamlit run streamlit_app.py
"""
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from graph import run_pipeline
from report_generator import generate_pdf_report
from agents.interview_agent import start_persona_interview

st.set_page_config(page_title="Synthetic Persona Research Platform", layout="wide")
st.title("Synthetic Persona Research Platform")

# ---------------------------------------------------------------------------
# 1. Research setup form -> reuses run_pipeline() unchanged
# ---------------------------------------------------------------------------
with st.form("research_form"):
    product_description = st.text_area(
        "Product description",
        value=st.session_state.get("product_description", ""),
        height=90,
    )
    target_audience = st.text_area(
        "Target audience",
        value=st.session_state.get("target_audience", ""),
        height=70,
    )
    research_goal = st.text_area(
        "Research goal",
        value=st.session_state.get("research_goal", ""),
        height=70,
    )
    col1, col2 = st.columns(2)
    with col1:
        num_personas = st.slider("Number of personas", 2, 10, 5)
    with col2:
        num_questions = st.slider("Number of survey questions", 3, 12, 6)
    submitted = st.form_submit_button("Run pipeline")

if submitted:
    if not (product_description and target_audience):
        st.error("Product description and target audience are required.")
    else:
        with st.spinner("Running persona -> survey -> response -> insight pipeline..."):
            try:
                final_state = run_pipeline(
                    product_description=product_description,
                    target_audience=target_audience,
                    research_goal=research_goal,
                    num_personas=num_personas,
                    num_questions=num_questions,
                    thread_id=f"streamlit-{uuid.uuid4().hex[:8]}",
                )
            except Exception as e:
                st.error(f"Pipeline run failed: {e}")
                final_state = None

        if final_state is not None:
            st.session_state["final_state"] = final_state
            st.session_state["product_description"] = product_description
            st.session_state["target_audience"] = target_audience
            st.session_state["research_goal"] = research_goal
            # New pipeline run -> old interview sessions no longer apply
            st.session_state["interview_sessions"] = {}

# ---------------------------------------------------------------------------
# 2. Visual persona cards
# ---------------------------------------------------------------------------
final_state = st.session_state.get("final_state")

if final_state:
    personas = final_state.get("personas", [])

    st.header("Generated Personas")
    cols = st.columns(2)
    for i, p in enumerate(personas):
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(p.name)
                st.caption(f"{p.age} years old — {p.occupation}")
                st.markdown(f"**Personality traits:** {', '.join(p.personality_traits)}")
                st.markdown(f"**Behavioral patterns:** {', '.join(p.behavioral_patterns)}")
                st.markdown(f"**Psychological profile:** {p.psychological_profile}")
                st.markdown(f"**Goals:** {', '.join(p.goals)}")
                st.markdown(f"**Pain points:** {', '.join(p.pain_points)}")
                st.markdown(f"**Tech savviness:** {p.tech_savviness}")
                st.markdown(f"_{p.persona_summary}_")

    # -----------------------------------------------------------------
    # 3. Interview Mode: user <-> selected persona, isolated per persona
    # -----------------------------------------------------------------
    st.header("Interview Mode")
    st.caption("Converse directly with a selected persona about the product.")

    if personas:
        if "interview_sessions" not in st.session_state:
            st.session_state["interview_sessions"] = {}
        sessions = st.session_state["interview_sessions"]

        selected_name = st.selectbox("Select a persona to interview", [p.name for p in personas])
        selected_persona = next(p for p in personas if p.name == selected_name)

        if selected_persona.id not in sessions:
            sessions[selected_persona.id] = start_persona_interview(
                selected_persona, product_description=final_state["product_description"]
            )
        session = sessions[selected_persona.id]

        for msg in session.history:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            with st.chat_message(role):
                st.write(msg.content)

        user_input = st.chat_input(f"Ask {selected_persona.name} something...")
        if user_input:
            with st.chat_message("user"):
                st.write(user_input)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        reply = session.respond(user_input)
                    except RuntimeError as e:
                        reply = f"(interview error: {e})"
                st.write(reply)

    # -----------------------------------------------------------------
    # 4. PDF report (reuses generate_pdf_report() unchanged)
    # -----------------------------------------------------------------
    st.header("Report")
    if st.button("Generate PDF report"):
        with st.spinner("Generating PDF..."):
            import os
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = generate_pdf_report(
                final_state, os.path.join(output_dir, "synthetic_research_report.pdf")
            )
        st.success(f"PDF written to {pdf_path}")
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF", f, file_name="synthetic_research_report.pdf")
else:
    st.info("Fill in the form above and click \"Run pipeline\" to generate personas.")

"""
Runs the full pipeline end-to-end using YOUR product as the example:

    Placement Prep AI — Campus-to-Corporate Readiness Platform

Two things run here:

1. SURVEY MODE (core project requirement):
   persona_agent -> survey_agent -> response_agent -> insight_agent -> PDF
   i.e. validate the *product idea itself* with synthetic student personas
   representing your target audience.

2. INTERVIEW MODE (bonus, specific to Placement Prep AI):
   generate a company-specific interviewer persona and run one scripted
   turn to show the memory-carrying conversation + feedback agent.

Usage:
    pip install -r requirements.txt
    cp .env.example .env   # then add your ANTHROPIC_API_KEY
    python main.py
"""
import os
from graph import run_pipeline
from report_generator import generate_pdf_report
from agents.interview_agent import generate_interview_persona, InterviewSession


# Portable, project-relative output directory (works on any machine, not just
# the sandboxed /mnt/user-data/ container path this project was developed in).
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


PRODUCT_DESCRIPTION = (
    "Placement Prep AI: a Campus-to-Corporate Readiness Platform that helps "
    "final-year college students prepare for company-specific placement interviews. "
    "It uses synthetic interviewer personas (e.g. 'Strict Infosys HR', "
    "'Friendly TCS Tech Lead') to simulate real HR, technical and coding rounds, "
    "gives resume feedback via synthetic recruiter personas, and detects weak "
    "areas in communication, technical depth and confidence."
)

TARGET_AUDIENCE = (
    "Final-year engineering/college students preparing for campus placements, "
    "including students at tier-2/tier-3 colleges with little access to real mock "
    "interviews; also Training & Placement (T&P) cell officers who want to track "
    "batch-wide readiness; also companies wanting a standardized screening simulation."
)

RESEARCH_GOAL = (
    "Decide which features to prioritize for the MVP launch this placement season: "
    "mock interview personas, coding round simulation, resume feedback, or "
    "weak-area analytics dashboards for T&P cells."
)


def run_survey_mode():
    print("Running Survey Mode pipeline (persona -> survey -> responses -> insight)...")
    final_state = run_pipeline(
        product_description=PRODUCT_DESCRIPTION,
        target_audience=TARGET_AUDIENCE,
        research_goal=RESEARCH_GOAL,
        num_personas=5,
        num_questions=6,
        thread_id="placement-prep-mvp-research",
    )

    print("\n--- Pipeline log ---")
    for line in final_state["log"]:
        print(line)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pdf_path = generate_pdf_report(final_state, os.path.join(OUTPUT_DIR, "synthetic_research_report.pdf"))
    print(f"\nPDF report written to: {pdf_path}")
    return final_state


def run_interview_mode_demo():
    print("\nRunning Interview Mode demo (memory-carrying mock interview)...")
    persona = generate_interview_persona(company="Infosys", round_type="HR")
    print(f"Generated interviewer persona: {persona.name} — {persona.role}")

    session = InterviewSession(persona)
    opening = session.opening_line()
    print(f"\n{persona.name}: {opening}")

    student_reply = "Hi, I'm a final-year CSE student. I'm a bit nervous but excited for this opportunity."
    print(f"Candidate: {student_reply}")
    interviewer_reply = session.respond(student_reply)
    print(f"{persona.name}: {interviewer_reply}")

    feedback = session.get_feedback()
    print("\n--- Interview Feedback (weak-area detection) ---")
    print(feedback.model_dump_json(indent=2))
    return feedback


if __name__ == "__main__":
    run_survey_mode()
    run_interview_mode_demo()

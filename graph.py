"""
Wires the four agents into a single LangGraph StateGraph:

    persona_agent -> survey_agent -> response_agent -> insight_agent -> END

Memory: we attach a MemorySaver checkpointer. Every invoke() call with a
thread_id persists the full GraphState after each node, so:
  - you can resume/inspect a run later using the same thread_id
  - you can branch (e.g. re-run just the survey with edited questions)
    without re-generating personas, by feeding partial state back in
  - multiple products/runs stay isolated by thread_id

This is what satisfies the "agent should take up memory" requirement at
the pipeline level (persona -> survey -> insight all share/carry state).
Interview-mode's turn-by-turn conversational memory is handled separately
in agents/interview_agent.py (InterviewSession), since that's a different
kind of memory (message history, not pipeline state).
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import GraphState
from agents.persona_agent import persona_agent_node
from agents.survey_agent import survey_agent_node
from agents.response_agent import response_agent_node
from agents.insight_agent import insight_agent_node


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("persona_agent", persona_agent_node)
    graph.add_node("survey_agent", survey_agent_node)
    graph.add_node("response_agent", response_agent_node)
    graph.add_node("insight_agent", insight_agent_node)

    graph.set_entry_point("persona_agent")
    graph.add_edge("persona_agent", "survey_agent")
    graph.add_edge("survey_agent", "response_agent")
    graph.add_edge("response_agent", "insight_agent")
    graph.add_edge("insight_agent", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


def run_pipeline(product_description: str, target_audience: str, research_goal: str,
                  num_personas: int = 5, num_questions: int = 6, thread_id: str = "default-run"):
    app = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: GraphState = {
        "product_description": product_description,
        "target_audience": target_audience,
        "research_goal": research_goal,
        "num_personas": num_personas,
        "num_questions": num_questions,
        "thread_id": thread_id,
        "log": [],
    }

    final_state = app.invoke(initial_state, config=config)
    return final_state


def get_run_history(thread_id: str):
    """Inspect a previous run's checkpointed state by thread_id."""
    app = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    return app.get_state(config)

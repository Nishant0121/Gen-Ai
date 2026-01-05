from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.agents import curator_agent, sme_agent, architect_agent

def create_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("curator", curator_agent)
    workflow.add_node("sme", sme_agent)
    workflow.add_node("architect", architect_agent)

    workflow.set_entry_point("curator")
    workflow.add_edge("curator", "sme")
    workflow.add_edge("sme", "architect")
    workflow.add_edge("architect", END)

    return workflow.compile()

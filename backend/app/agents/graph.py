from langgraph.graph import END, StateGraph

from app.agents.nodes.bear import bear_node
from app.agents.nodes.bull import bull_node
from app.agents.nodes.execute import execute_node
from app.agents.nodes.ingest import ingest_node
from app.agents.nodes.judge import judge_node
from app.agents.nodes.log_rejection import log_rejection_node
from app.agents.nodes.risk import risk_node
from app.schemas.agent import AgentState


def _route(state: AgentState) -> str:
    return "execute" if state["risk"].approved else "log_rejection"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("bull_agent", bull_node)
    graph.add_node("bear_agent", bear_node)
    graph.add_node("judge_agent", judge_node)
    graph.add_node("risk_agent", risk_node)
    graph.add_node("execute", execute_node)
    graph.add_node("log_rejection", log_rejection_node)

    graph.set_entry_point("ingest")
    # Fan out to the bull and bear debaters in parallel...
    graph.add_edge("ingest", "bull_agent")
    graph.add_edge("ingest", "bear_agent")
    # ...then fan in to the judge, which runs once both sides have argued.
    graph.add_edge("bull_agent", "judge_agent")
    graph.add_edge("bear_agent", "judge_agent")
    graph.add_edge("judge_agent", "risk_agent")
    graph.add_conditional_edges(
        "risk_agent",
        _route,
        {"execute": "execute", "log_rejection": "log_rejection"},
    )
    graph.add_edge("execute", END)
    graph.add_edge("log_rejection", END)
    return graph.compile()

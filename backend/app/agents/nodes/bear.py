from app.schemas.agent import AgentState
from app.services import llm


def bear_node(state: AgentState) -> AgentState:
    """Bear debater. Returns only its own key so it can run in parallel with the
    bull node without colliding on a shared state channel."""
    arg = llm.debate_bear(state["market"], state["portfolio"])
    return {"bear": arg}

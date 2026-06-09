from app.schemas.agent import AgentState
from app.services import llm


def bull_node(state: AgentState) -> AgentState:
    """Bull debater. Returns only its own key so it can run in parallel with the
    bear node without colliding on a shared state channel."""
    arg = llm.debate_bull(state["market"], state["portfolio"])
    return {"bull": arg}

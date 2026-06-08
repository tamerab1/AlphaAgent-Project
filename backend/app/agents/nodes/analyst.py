from app.schemas.agent import AgentState
from app.services import llm


def analyst_node(state: AgentState) -> AgentState:
    decision = llm.analyze(state["market"], state["portfolio"])
    log = state.get("log", [])
    log.append(f"analyst: {decision.action} ({decision.confidence:.0%})")
    return {"analyst": decision, "log": log}

from app.agents.risk import assess_risk
from app.schemas.agent import AgentState


def risk_node(state: AgentState) -> AgentState:
    decision = assess_risk(state["analyst"], state["portfolio"], state["market"])
    verdict = "approved" if decision.approved else "rejected"
    log = state.get("log", [])
    log.append(f"risk: {verdict} - {decision.reason}")
    return {"risk": decision, "log": log}

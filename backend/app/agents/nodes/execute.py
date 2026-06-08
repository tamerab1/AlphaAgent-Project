from app.schemas.agent import AgentState


def execute_node(state: AgentState) -> AgentState:
    analyst = state["analyst"]
    log = state.get("log", [])
    log.append(
        f"execute: {analyst.action} {analyst.symbol} "
        f"at {state['risk'].adjusted_pct:.0%}"
    )
    return {"executed": True, "log": log}

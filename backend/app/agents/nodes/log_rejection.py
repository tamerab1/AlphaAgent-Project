from app.schemas.agent import AgentState


def log_rejection_node(state: AgentState) -> AgentState:
    log = state.get("log", [])
    log.append(f"rejected: {state['risk'].reason}")
    return {"executed": False, "log": log}

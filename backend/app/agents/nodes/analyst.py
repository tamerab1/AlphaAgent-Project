from app.schemas.agent import AgentState
from app.services import llm


def analyst_node(state: AgentState) -> AgentState:
    chart_image = state.get("chart_image")
    if chart_image:
        decision = llm.analyze(state["market"], state["portfolio"], chart_image)
    else:
        decision = llm.analyze(state["market"], state["portfolio"])
    log = state.get("log", [])
    msg = f"analyst: {decision.action} ({decision.confidence:.0%})"
    if decision.target_price is not None and decision.stop_loss is not None:
        msg += (
            f" | target {decision.target_price:.2f} / " f"stop {decision.stop_loss:.2f}"
        )
    log.append(msg)
    return {"analyst": decision, "log": log}

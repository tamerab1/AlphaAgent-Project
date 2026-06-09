from app.schemas.agent import AgentState
from app.services import llm


def judge_node(state: AgentState) -> AgentState:
    """Head of desk: weighs the bull vs bear cases into the final decision.

    Writes the decision under the ``analyst`` key so the downstream risk and
    execute nodes continue to work unchanged.
    """
    decision = llm.judge(
        state["market"],
        state["portfolio"],
        state["bull"],
        state["bear"],
        state.get("chart_image"),
    )
    log = state.get("log", [])
    msg = f"judge: {decision.action} ({decision.confidence:.0%})"
    if decision.target_price is not None and decision.stop_loss is not None:
        msg += (
            f" | target {decision.target_price:.2f} / stop {decision.stop_loss:.2f}"
        )
    log.append(msg)
    return {"analyst": decision, "log": log}

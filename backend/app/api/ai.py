import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents import build_graph
from app.api.deps import get_portfolio_or_404, loads_json
from app.db.session import get_db
from app.models import AgentRun, Portfolio, Position, Trade
from app.schemas.agent import ChartReading, PortfolioSnapshot
from app.schemas.api import AgentRunOut, AnalyzeRequest, ChartReadRequest, NewsItem
from app.services import llm, market_data

_DEFAULT_NEWS_SYMBOLS = ["BTC", "ETH", "SOL", "NVDA", "AAPL", "TSLA", "MSFT", "SPY"]

router = APIRouter(prefix="/api", tags=["ai"])

NODE_NAMES = {"ingest", "analyst_agent", "risk_agent", "execute", "log_rejection"}


@router.get("/ai/{portfolio_id}/logs", response_model=list[AgentRunOut])
def ai_logs(portfolio_id: int, db: Session = Depends(get_db)):
    get_portfolio_or_404(db, portfolio_id)
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.portfolio_id == portfolio_id)
        .order_by(AgentRun.created_at.desc())
        .all()
    )
    return [
        AgentRunOut(
            id=r.id,
            symbol=r.symbol,
            analyst=loads_json(r.analyst_json),
            risk=loads_json(r.risk_json),
            executed=r.executed,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/ai/news", response_model=list[NewsItem])
def get_news(symbol: str | None = None):
    """Return AI-tagged news items for one symbol or a default global basket."""
    targets = [symbol.strip().upper()] if symbol else _DEFAULT_NEWS_SYMBOLS
    items: list[NewsItem] = []
    for sym in targets:
        data = market_data.get_market_data(sym)
        for headline in data.headlines:
            tag = llm.analyze_headline_sentiment(headline, sym)
            # Deterministic but varied timestamp so the feed looks live
            minutes_ago = abs(hash(headline + sym)) % 90
            items.append(
                NewsItem(
                    id=f"{sym}-{abs(hash(headline)) % 999999}",
                    headline=headline,
                    symbol=sym,
                    sentiment=tag.sentiment,
                    summary=tag.summary,
                    source="Market Intelligence",
                    published_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
                )
            )
    return sorted(items, key=lambda x: x.published_at, reverse=True)


@router.post("/ai/read-chart", response_model=ChartReading)
def ai_read_chart(body: ChartReadRequest):
    """Multimodal visual read of a chart image, independent of the trade flow."""
    if not body.chart_image:
        raise HTTPException(status_code=400, detail="chart_image is required")
    return llm.read_chart(body.chart_image, body.symbol)


@router.post("/ai/{portfolio_id}/analyze-chart")
async def analyze_chart(
    portfolio_id: int, body: AnalyzeRequest, db: Session = Depends(get_db)
):
    portfolio = get_portfolio_or_404(db, portfolio_id)
    snapshot = _portfolio_snapshot(portfolio, body.symbol)
    # Persistence runs inside the streaming generator (after the endpoint has
    # returned), where the request-scoped session is no longer reliable. Capture
    # the engine now and open a fresh session bound to it when we persist.
    bind = db.get_bind()
    graph = build_graph()
    state = {
        "symbol": body.symbol,
        "portfolio": snapshot,
        "chart_image": body.chart_image,
    }

    async def event_stream():
        final: dict = {}
        async for event in graph.astream_events(state, version="v2"):
            if event.get("event") != "on_chain_end":
                continue
            name = event.get("name")
            output = event["data"].get("output")
            if name not in NODE_NAMES or not isinstance(output, dict):
                continue
            final.update(output)
            yield f"data: {json.dumps(_node_payload(name, output))}\n\n"
        with Session(bind=bind) as write_db:
            portfolio_row = write_db.get(Portfolio, portfolio_id)
            if portfolio_row is not None:
                _persist(
                    write_db,
                    portfolio_row,
                    body.symbol,
                    final,
                    snapshot.total_value,
                )
        done = {"node": "done", "executed": bool(final.get("executed"))}
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _portfolio_snapshot(portfolio: Portfolio, symbol: str) -> PortfolioSnapshot:
    total = portfolio.cash_balance
    exposure = 0.0
    for pos in portfolio.positions:
        value = market_data.get_market_data(pos.symbol).price * pos.qty
        total += value
        if pos.symbol == symbol:
            exposure += value
    return PortfolioSnapshot(
        cash_balance=portfolio.cash_balance,
        total_value=total,
        symbol_exposure=exposure,
    )


def _node_payload(name: str, output: dict) -> dict:
    payload: dict = {"node": name}
    log = output.get("log")
    if log:
        payload["message"] = log[-1]
    for key in ("market", "analyst", "risk"):
        if key in output:
            payload[key] = output[key].model_dump()
    if "executed" in output:
        payload["executed"] = output["executed"]
    return payload


def _persist(
    db: Session,
    portfolio: Portfolio,
    symbol: str,
    final: dict,
    total_value: float,
) -> None:
    analyst = final.get("analyst")
    risk = final.get("risk")
    market = final.get("market")
    executed = bool(final.get("executed"))
    db.add(
        AgentRun(
            portfolio_id=portfolio.id,
            symbol=symbol,
            analyst_json=json.dumps(analyst.model_dump()) if analyst else None,
            risk_json=json.dumps(risk.model_dump()) if risk else None,
            executed=executed,
        )
    )
    if executed and analyst and risk and market:
        _apply_trade(db, portfolio, symbol, analyst, risk, market, total_value)
    db.commit()


def _apply_trade(db, portfolio, symbol, analyst, risk, market, total_value) -> None:
    price = market.price
    existing = next((p for p in portfolio.positions if p.symbol == symbol), None)
    side = analyst.action

    if side == "BUY":
        dollars = risk.adjusted_pct * total_value
        qty = dollars / price if price else 0.0
        portfolio.cash_balance -= dollars
        if existing:
            new_qty = existing.qty + qty
            existing.avg_price = (
                (existing.avg_price * existing.qty + price * qty) / new_qty
                if new_qty
                else price
            )
            existing.qty = new_qty
        else:
            db.add(
                Position(
                    portfolio_id=portfolio.id,
                    symbol=symbol,
                    qty=qty,
                    avg_price=price,
                )
            )
    else:  # SELL (approved only when a position exists)
        qty = risk.adjusted_pct * existing.qty
        portfolio.cash_balance += qty * price
        existing.qty -= qty

    db.add(
        Trade(
            portfolio_id=portfolio.id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            rationale=risk.reason,
        )
    )

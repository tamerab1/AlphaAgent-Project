import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents import build_graph
from app.api.deps import get_optional_user_id, get_portfolio_or_404, loads_json
from app.core.config import settings
from app.db.session import get_db
from app.models import AgentRun, Portfolio, Position, Trade
from app.schemas.agent import ChartReading, PortfolioSnapshot
from app.schemas.api import AgentRunOut, AnalyzeRequest, ChartReadRequest, NewsItem
from app.services import llm, market_data

_DEFAULT_NEWS_SYMBOLS = ["BTC", "ETH", "SOL", "NVDA", "AAPL", "TSLA", "MSFT", "SPY"]

# Short-term in-memory cache — prevents re-running the full LangGraph pipeline
# for the same symbol within the TTL window (Render free-tier resource guard).
# Gated on openai_api_key so mock/test runs always execute fresh; only live
# LLM calls are expensive enough to need this protection.
_ANALYSIS_CACHE: dict[str, tuple[float, list[dict]]] = {}
_ANALYSIS_TTL = 120.0  # seconds

router = APIRouter(prefix="/api", tags=["ai"])

NODE_NAMES = {
    "ingest",
    "bull_agent",
    "bear_agent",
    "judge_agent",
    "risk_agent",
    "execute",
    "log_rejection",
}


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
        for entry in market_data.get_news_data(sym):
            headline = entry["headline"]
            url = entry.get("url") or None
            tag = llm.analyze_headline_sentiment(headline, sym)
            minutes_ago = abs(hash(headline + sym)) % 90
            items.append(
                NewsItem(
                    id=f"{sym}-{abs(hash(headline)) % 999999}",
                    headline=headline,
                    symbol=sym,
                    sentiment=tag.sentiment,
                    summary=tag.summary,
                    sentiment_breakdown=tag.sentiment_breakdown,
                    source="Market Intelligence",
                    url=url,
                    published_at=datetime.now(timezone.utc)
                    - timedelta(minutes=minutes_ago),
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
    portfolio_id: int,
    body: AnalyzeRequest,
    db: Session = Depends(get_db),
    caller_id: Optional[UUID] = Depends(get_optional_user_id),
):
    portfolio = get_portfolio_or_404(db, portfolio_id)
    snapshot = _portfolio_snapshot(portfolio, body.symbol)
    # Resolve the owner: use the portfolio's stored user_id if the caller didn't
    # send a JWT (e.g. legacy anonymous sessions); prefer the JWT when present.
    owner_id: Optional[UUID] = caller_id or portfolio.user_id
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
    cache_key = body.symbol.upper()

    async def event_stream():
        # ── Cache hit (live LLM mode only): replay events without re-running ──
        if settings.openai_api_key:
            hit = _ANALYSIS_CACHE.get(cache_key)
            if hit and (time.monotonic() - hit[0]) < _ANALYSIS_TTL:
                for ev in hit[1]:
                    yield f"data: {json.dumps(ev)}\n\n"
                cached_done = {"node": "done", "executed": False, "cached": True}
                yield f"data: {json.dumps(cached_done)}\n\n"
                return

        # ── Live run with a hard total-budget timeout guard ──
        final: dict = {}
        collected: list[dict] = []
        timed_out = False
        try:
            async with asyncio.timeout(35.0):
                async for event in graph.astream_events(state, version="v2"):
                    if event.get("event") != "on_chain_end":
                        continue
                    name = event.get("name")
                    output = event["data"].get("output")
                    if name not in NODE_NAMES or not isinstance(output, dict):
                        continue
                    final.update(output)
                    payload = _node_payload(name, output)
                    collected.append(payload)
                    yield f"data: {json.dumps(payload)}\n\n"
        except TimeoutError:
            timed_out = True
            for ev in _timeout_fallback(cache_key):
                yield f"data: {json.dumps(ev)}\n\n"

        if timed_out:
            yield f"data: {json.dumps({'node': 'done', 'executed': False})}\n\n"
            return

        # ── Cache successful result (live LLM only — mock runs are instant) ──
        if collected and settings.openai_api_key:
            _ANALYSIS_CACHE[cache_key] = (time.monotonic(), collected)

        with Session(bind=bind) as write_db:
            portfolio_row = write_db.get(Portfolio, portfolio_id)
            if portfolio_row is not None:
                _persist(
                    write_db,
                    portfolio_row,
                    body.symbol,
                    final,
                    snapshot.total_value,
                    owner_id,
                )
        done = {"node": "done", "executed": bool(final.get("executed"))}
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _timeout_fallback(symbol: str) -> list[dict]:
    """Mock event sequence streamed when the LangGraph pipeline exceeds its budget."""
    return [
        {
            "node": "ingest",
            "message": f"Market intelligence for {symbol} (timeout — cached signals).",
        },
        {
            "node": "bull_agent",
            "bull": {
                "stance": "bull",
                "thesis": f"Live analysis for {symbol} could not complete in time.",
                "key_points": ["Pipeline timeout — using fallback signals."],
                "conviction": 0.0,
            },
            "message": f"Bull: Live analysis for {symbol} timed out.",
        },
        {
            "node": "bear_agent",
            "bear": {
                "stance": "bear",
                "thesis": f"Live analysis for {symbol} could not complete in time.",
                "key_points": ["Pipeline timeout — using fallback signals."],
                "conviction": 0.0,
            },
            "message": f"Bear: Live analysis for {symbol} timed out.",
        },
        {
            "node": "judge_agent",
            "analyst": {
                "action": "HOLD",
                "symbol": symbol,
                "reasoning": (
                    "Pipeline timed out — defaulting to HOLD to avoid "
                    "uninformed execution."
                ),
                "confidence": 0.0,
                "suggested_pct": 0.0,
                "target_price": None,
                "stop_loss": None,
            },
            "message": "HOLD — pipeline timeout.",
        },
        {
            "node": "risk_agent",
            "risk": {
                "approved": False,
                "reason": "Analysis timed out — no trade executed.",
                "adjusted_pct": 0.0,
            },
            "message": "Risk: trade rejected (timeout).",
        },
        {
            "node": "log_rejection",
            "message": "Trade not executed: analysis timed out.",
        },
    ]


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
    for key in ("market", "bull", "bear", "analyst", "risk"):
        if key in output:
            payload[key] = output[key].model_dump()
    # The bull/bear nodes don't write the log channel (they run in parallel);
    # surface their thesis as the stream message instead.
    if "message" not in payload and "bull" in output:
        payload["message"] = f"Bull: {output['bull'].thesis}"
    if "message" not in payload and "bear" in output:
        payload["message"] = f"Bear: {output['bear'].thesis}"
    if "executed" in output:
        payload["executed"] = output["executed"]
    return payload


def _persist(
    db: Session,
    portfolio: Portfolio,
    symbol: str,
    final: dict,
    total_value: float,
    user_id: Optional[UUID] = None,
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
        _apply_trade(db, portfolio, symbol, analyst, risk, market, total_value, user_id)
    db.commit()


def _apply_trade(
    db, portfolio, symbol, analyst, risk, market, total_value, user_id=None
) -> None:
    # Fetch the freshest available execution price: Binance for crypto,
    # falling back to the already-fetched market data price.
    price = market_data.get_execution_price(symbol)
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
            user_id=user_id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            rationale=risk.reason,
        )
    )

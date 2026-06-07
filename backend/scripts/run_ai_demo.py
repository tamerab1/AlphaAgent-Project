import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.graph import build_graph  # noqa: E402
from ai.schemas import MarketData, PortfolioSnapshot  # noqa: E402


def main() -> None:
    graph = build_graph()
    state = {
        "symbol": "AAPL",
        "market": MarketData(
            symbol="AAPL",
            price=180.0,
            rsi=25.0,
            headlines=["AAPL dips on profit-taking"],
        ),
        "portfolio": PortfolioSnapshot(
            cash_balance=20000.0, total_value=100000.0, symbol_exposure=0.0
        ),
    }

    result = graph.invoke(state)

    print(f"\n=== Agent run for {result['market'].symbol} ===")
    for line in result["log"]:
        print(f"  - {line}")
    print(f"\nAnalyst: {result['analyst'].model_dump()}")
    print(f"Risk:    {result['risk'].model_dump()}")
    print(f"Executed: {result.get('executed')}")


if __name__ == "__main__":
    main()

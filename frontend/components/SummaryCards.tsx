import type { PortfolioStatus } from "@/lib/api";
import {
  formatCurrency,
  formatPercent,
  formatSignedCurrency,
  pnlColor,
} from "@/lib/format";

function Card({
  label,
  value,
  valueClass = "text-white",
  sub,
}: {
  label: string;
  value: string;
  valueClass?: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${valueClass}`}>{value}</p>
      {sub && <p className="mt-1 text-sm text-muted">{sub}</p>}
    </div>
  );
}

export default function SummaryCards({ status }: { status: PortfolioStatus }) {
  const costBasis = status.total_value - status.unrealized_pnl;
  const pnlPct = costBasis > 0 ? (status.unrealized_pnl / costBasis) * 100 : 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card label="Total Value" value={formatCurrency(status.total_value)} />
      <Card label="Cash" value={formatCurrency(status.cash_balance)} />
      <Card
        label="Positions Value"
        value={formatCurrency(status.positions_value)}
      />
      <Card
        label="Unrealized P&L"
        value={formatSignedCurrency(status.unrealized_pnl)}
        valueClass={pnlColor(status.unrealized_pnl)}
        sub={formatPercent(pnlPct)}
      />
    </div>
  );
}

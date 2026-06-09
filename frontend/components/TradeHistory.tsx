import type { TradeOut } from "@/lib/api";
import { formatCurrency, formatQty, formatTime } from "@/lib/format";

function SideBadge({ side }: { side: string }) {
  const isBuy = side.toUpperCase() === "BUY";
  const cls = isBuy
    ? "bg-positive/15 text-positive"
    : "bg-negative/15 text-negative";
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${cls}`}>
      {side.toUpperCase()}
    </span>
  );
}

export default function TradeHistory({ trades }: { trades: TradeOut[] }) {
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-5 py-3">
        <h2 className="text-lg font-semibold">Trade History</h2>
      </div>
      {trades.length === 0 ? (
        <p className="px-5 py-8 text-center text-muted">No trades yet.</p>
      ) : (
        <ul className="divide-y divide-border">
          {trades.map((t) => (
            <li key={t.id} className="px-5 py-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <SideBadge side={t.side} />
                  <span className="font-medium">{t.symbol}</span>
                  <span className="text-sm text-muted">
                    {formatQty(t.qty)} @ {formatCurrency(t.price)}
                  </span>
                </div>
                <span className="text-xs text-muted">
                  {formatTime(t.created_at)}
                </span>
              </div>
              {t.rationale && (
                <p className="mt-1 text-sm text-muted">{t.rationale}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

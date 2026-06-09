import type { PositionOut } from "@/lib/api";
import {
  formatCurrency,
  formatQty,
  formatSignedCurrency,
  pnlColor,
} from "@/lib/format";

export default function PositionsTable({
  positions,
}: {
  positions: PositionOut[];
}) {
  return (
    <div className="rounded-lg border border-border bg-surface">
      <div className="border-b border-border px-5 py-3">
        <h2 className="text-lg font-semibold">Open Positions</h2>
      </div>
      {positions.length === 0 ? (
        <p className="px-5 py-8 text-center text-muted">No open positions yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted">
                <th className="px-5 py-3 font-medium">Symbol</th>
                <th className="px-5 py-3 font-medium text-right">Qty</th>
                <th className="px-5 py-3 font-medium text-right">Avg Price</th>
                <th className="px-5 py-3 font-medium text-right">Current</th>
                <th className="px-5 py-3 font-medium text-right">Market Value</th>
                <th className="px-5 py-3 font-medium text-right">Unrealized P&L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.symbol} className="border-t border-border">
                  <td className="px-5 py-3 font-medium">{p.symbol}</td>
                  <td className="px-5 py-3 text-right">{formatQty(p.qty)}</td>
                  <td className="px-5 py-3 text-right">
                    {formatCurrency(p.avg_price)}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {formatCurrency(p.current_price)}
                  </td>
                  <td className="px-5 py-3 text-right">
                    {formatCurrency(p.market_value)}
                  </td>
                  <td className={`px-5 py-3 text-right ${pnlColor(p.unrealized_pnl)}`}>
                    {formatSignedCurrency(p.unrealized_pnl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

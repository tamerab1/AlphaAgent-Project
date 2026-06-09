// Display formatters shared across dashboard components.

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

export function formatCurrency(value: number): string {
  return usd.format(value);
}

export function formatQty(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatSignedCurrency(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${usd.format(value)}`;
}

// Tailwind text color for a gain/loss number.
export function pnlColor(value: number): string {
  if (value > 0) return "text-positive";
  if (value < 0) return "text-negative";
  return "text-muted";
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

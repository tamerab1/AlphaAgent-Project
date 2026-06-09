import type { ChartReading } from "@/lib/api";

const BIAS_STYLES: Record<ChartReading["bias"], string> = {
  bullish: "bg-positive/15 text-positive",
  bearish: "bg-negative/15 text-negative",
  neutral: "bg-border text-muted",
};

export default function ChartReadingCard({
  reading,
}: {
  reading: ChartReading;
}) {
  return (
    <div className="mt-3 rounded-md border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Chart reading</h3>
        <span
          className={`rounded px-2 py-0.5 text-xs font-medium capitalize ${BIAS_STYLES[reading.bias]}`}
        >
          {reading.bias}
        </span>
      </div>

      <p className="mt-2 text-sm text-muted">{reading.summary}</p>

      <div className="mt-3 grid grid-cols-1 gap-1 sm:grid-cols-2">
        {reading.support_levels.length > 0 && (
          <p className="text-sm text-muted">
            <span className="text-positive">Support:</span>{" "}
            {reading.support_levels.map((l) => `$${l.toFixed(2)}`).join(", ")}
          </p>
        )}
        {reading.resistance_levels.length > 0 && (
          <p className="text-sm text-muted">
            <span className="text-negative">Resistance:</span>{" "}
            {reading.resistance_levels.map((l) => `$${l.toFixed(2)}`).join(", ")}
          </p>
        )}
      </div>

      {reading.patterns.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {reading.patterns.map((p, i) => (
            <span
              key={i}
              className="rounded-full border border-border px-2 py-0.5 text-xs text-muted"
            >
              {p}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

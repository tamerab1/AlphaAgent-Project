// Streaming client for POST /api/ai/{id}/analyze-chart.
// The endpoint emits Server-Sent-Event frames ("data: {json}\n\n"). EventSource
// only supports GET, so we read the response body and parse frames by hand.

import {
  API_BASE_URL,
  getAuthToken,
  type AnalystDecision,
  type RiskDecision,
} from "@/lib/api";

export interface MarketData {
  symbol: string;
  price: number;
  rsi: number;
  headlines: string[];
}

// One decoded SSE frame. `node` is the graph node name, or "done" for the
// terminal frame. Other fields appear depending on which node emitted it.
export interface AnalyzeEvent {
  node:
    | "ingest"
    | "analyst_agent"
    | "risk_agent"
    | "execute"
    | "log_rejection"
    | "done";
  message?: string;
  market?: MarketData;
  analyst?: AnalystDecision;
  risk?: RiskDecision;
  executed?: boolean;
}

export async function streamAnalyze(
  portfolioId: number,
  symbol: string,
  onEvent: (event: AnalyzeEvent) => void,
  signal?: AbortSignal,
  chartImage?: string | null
): Promise<void> {
  const body: { symbol: string; chart_image?: string } = { symbol };
  if (chartImage) body.chart_image = chartImage;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getAuthToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(
    `${API_BASE_URL}/api/ai/${portfolioId}/analyze-chart`,
    {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
    }
  );

  if (!res.ok || !res.body) {
    const detail = await res.text().catch(() => "");
    throw new Error(
      `${res.status} ${res.statusText}${detail ? `: ${detail}` : ""}`
    );
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as AnalyzeEvent);
      } catch {
        // ignore malformed frame
      }
    }
  }
}

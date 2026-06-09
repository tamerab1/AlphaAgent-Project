"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createPortfolio,
  getAgentLogs,
  getPortfolioStatus,
  type AgentRunOut,
  type PortfolioStatus,
} from "@/lib/api";
import SummaryCards from "@/components/SummaryCards";
import PositionsTable from "@/components/PositionsTable";
import ActionLog from "@/components/ActionLog";
import ModeToggle from "@/components/ModeToggle";
import AnalysisPanel from "@/components/AnalysisPanel";

const STORAGE_KEY = "alphaagent_portfolio_id";

// Resolve a portfolio to display: reuse the stored id, else create a demo one.
async function resolvePortfolioId(): Promise<number> {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      await getPortfolioStatus(Number(stored));
      return Number(stored);
    } catch {
      // fall through and create a fresh portfolio
    }
  }
  const created = await createPortfolio("demo");
  window.localStorage.setItem(STORAGE_KEY, String(created.id));
  return created.id;
}

export default function DashboardPage() {
  const [portfolioId, setPortfolioId] = useState<number | null>(null);
  const [status, setStatus] = useState<PortfolioStatus | null>(null);
  const [logs, setLogs] = useState<AgentRunOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: number) => {
    const [statusRes, logsRes] = await Promise.all([
      getPortfolioStatus(id),
      getAgentLogs(id),
    ]);
    setStatus(statusRes);
    setLogs(logsRes);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const id = await resolvePortfolioId();
        if (!active) return;
        setPortfolioId(id);
        await load(id);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load.");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-accent">AlphaAgent</h1>
          <p className="text-sm text-muted">AI Trading Portfolio Manager</p>
        </div>
        {portfolioId !== null && <ModeToggle portfolioId={portfolioId} />}
      </header>

      {loading && (
        <p className="py-16 text-center text-muted">Loading portfolio…</p>
      )}

      {error && !loading && (
        <div className="rounded-lg border border-negative/40 bg-negative/10 p-5 text-negative">
          <p className="font-medium">Could not reach the backend.</p>
          <p className="mt-1 text-sm">{error}</p>
        </div>
      )}

      {!loading && !error && status && (
        <div className="space-y-6">
          <SummaryCards status={status} />
          {portfolioId !== null && (
            <AnalysisPanel
              portfolioId={portfolioId}
              onComplete={() => load(portfolioId)}
            />
          )}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <PositionsTable positions={status.positions} />
            <ActionLog runs={logs} />
          </div>
        </div>
      )}
    </main>
  );
}

"use client";

import { useState, useEffect, useRef } from "react";
import { Activity, ChevronDown, User, Settings, LogOut, Wifi, WifiOff } from "lucide-react";
import type { TradingMode } from "@/lib/api";

interface TopNavProps {
  mode: TradingMode;
  onModeChange: (mode: TradingMode) => void;
  apiConnected: boolean;
  portfolioUser?: string;
}

export default function TopNav({ mode, onModeChange, apiConnected, portfolioUser }: TopNavProps) {
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const isLive = mode === "live";

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <nav className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-surface px-4 lg:px-6">

      {/* ── Logo ── */}
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-accent">
          <Activity className="h-4 w-4 text-bg font-bold" strokeWidth={2.5} />
        </div>
        <span className="text-[17px] font-bold tracking-tight">
          <span className="text-accent">Alpha</span>
          <span className="text-white">Agent</span>
        </span>
        <span className="hidden rounded bg-accent/15 px-1.5 py-[3px] text-[9px] font-bold uppercase tracking-widest text-accent sm:block">
          AI PRO
        </span>
      </div>

      {/* ── SRS Trading Switch ── */}
      <div className="flex items-center gap-3">
        <div
          className={`flex items-center gap-1 rounded-full border p-1 transition-colors duration-500 ${
            isLive ? "border-positive/40 bg-positive/5" : "border-accent/30 bg-accent/5"
          }`}
        >
          <button
            onClick={() => onModeChange("paper")}
            className={`rounded-full px-3.5 py-1 text-xs font-semibold transition-all duration-300 ${
              !isLive
                ? "bg-accent text-bg shadow"
                : "text-muted hover:text-white"
            }`}
          >
            Paper
          </button>
          <button
            onClick={() => onModeChange("live")}
            className={`rounded-full px-3.5 py-1 text-xs font-semibold transition-all duration-300 ${
              isLive
                ? "bg-positive text-bg shadow"
                : "text-muted hover:text-white"
            }`}
          >
            Live
          </button>
        </div>

        {/* Pulsing mode indicator */}
        <div className="hidden items-center gap-1.5 sm:flex">
          <span className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${isLive ? "bg-positive" : "bg-accent"}`} />
            <span className={`relative inline-flex h-2 w-2 rounded-full ${isLive ? "bg-positive" : "bg-accent"}`} />
          </span>
          <span className={`text-[11px] font-semibold tracking-widest ${isLive ? "text-positive" : "text-accent"}`}>
            {isLive ? "LIVE" : "PAPER"}
          </span>
        </div>
      </div>

      {/* ── Right: Connection + Profile ── */}
      <div className="flex items-center gap-2.5">
        {/* API health */}
        <div
          className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
            apiConnected
              ? "border-positive/25 bg-positive/5 text-positive"
              : "border-negative/25 bg-negative/5 text-negative"
          }`}
        >
          {apiConnected
            ? <Wifi className="h-3 w-3" />
            : <WifiOff className="h-3 w-3" />}
          <span className="hidden sm:block">{apiConnected ? "Connected" : "Offline"}</span>
        </div>

        {/* Profile dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setProfileOpen((o) => !o)}
            className="flex items-center gap-2 rounded-full border border-border bg-surface2 px-3 py-1.5 text-sm transition-colors hover:border-muted/40"
          >
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/20 text-[10px] font-bold uppercase text-accent">
              {(portfolioUser ?? "D").charAt(0).toUpperCase()}
            </span>
            <span className="hidden text-xs text-muted sm:block capitalize">{portfolioUser ?? "Demo"}</span>
            <ChevronDown className={`h-3 w-3 text-muted transition-transform duration-200 ${profileOpen ? "rotate-180" : ""}`} />
          </button>

          {profileOpen && (
            <div className="animate-fade-in absolute right-0 top-full mt-1.5 w-44 rounded-xl border border-border bg-surface2 py-1.5 shadow-2xl">
              <button className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs text-muted transition-colors hover:bg-white/5 hover:text-white">
                <User className="h-3.5 w-3.5" /> Profile
              </button>
              <button className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs text-muted transition-colors hover:bg-white/5 hover:text-white">
                <Settings className="h-3.5 w-3.5" /> Settings
              </button>
              <div className="my-1 border-t border-border" />
              <button className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs text-negative transition-colors hover:bg-negative/5">
                <LogOut className="h-3.5 w-3.5" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}

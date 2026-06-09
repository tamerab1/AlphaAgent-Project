"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, ChevronDown, User, Settings, LogOut,
  Wifi, WifiOff, Menu, X,
  LayoutDashboard, ArrowLeftRight, Newspaper,
} from "lucide-react";
import type { TradingMode } from "@/lib/api";

interface TopNavProps {
  mode: TradingMode;
  onModeChange: (mode: TradingMode) => void;
  apiConnected: boolean;
  portfolioUser?: string;
  onSignOut?: () => void;
}

const NAV_LINKS = [
  { href: "/",       label: "Dashboard", icon: LayoutDashboard },
  { href: "/trades", label: "Trades",    icon: ArrowLeftRight  },
  { href: "/news",   label: "News",      icon: Newspaper       },
];

export default function TopNav({ mode, onModeChange, apiConnected, portfolioUser, onSignOut }: TopNavProps) {
  const [profileOpen,    setProfileOpen]    = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const profileRef    = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const isLive = mode === "live";

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(e.target as Node)) {
        setMobileMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Close mobile menu on route change
  useEffect(() => { setMobileMenuOpen(false); }, [pathname]);

  return (
    <div className="sticky top-0 z-50 relative">
      {/* ── Main nav bar ── */}
      <nav className="flex h-12 items-center justify-between border-b border-border bg-surface px-3 sm:h-14 lg:px-6">

        {/* ── Left: Logo + desktop nav ── */}
        <div className="flex items-center gap-2">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen((o) => !o)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-white/5 hover:text-white md:hidden"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen
              ? <X className="h-4 w-4" />
              : <Menu className="h-4 w-4" />}
          </button>

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-accent sm:h-7 sm:w-7">
              <Activity className="h-3.5 w-3.5 text-bg font-bold sm:h-4 sm:w-4" strokeWidth={2.5} />
            </div>
            <span className="text-[15px] font-bold tracking-tight sm:text-[17px]">
              <span className="text-accent">Alpha</span>
              <span className="text-white">Agent</span>
            </span>
          </Link>

          <span className="hidden rounded bg-accent/15 px-1.5 py-[3px] text-[9px] font-bold uppercase tracking-widest text-accent sm:block">
            AI PRO
          </span>

          {/* Desktop nav links */}
          <div className="ml-2 hidden items-center gap-0.5 md:flex">
            {NAV_LINKS.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  pathname === href
                    ? "bg-white/8 text-white"
                    : "text-muted hover:bg-white/5 hover:text-white"
                }`}
              >
                {label}
              </Link>
            ))}
          </div>
        </div>

        {/* ── Center: Paper/Live toggle ── */}
        <div className="flex items-center gap-2 sm:gap-3">
          <div
            className={`flex items-center gap-0.5 rounded-full border p-0.5 transition-colors duration-500 sm:gap-1 sm:p-1 ${
              isLive ? "border-positive/40 bg-positive/5" : "border-accent/30 bg-accent/5"
            }`}
          >
            <button
              onClick={() => onModeChange("paper")}
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all duration-300 sm:px-3.5 sm:text-xs ${
                !isLive ? "bg-accent text-bg shadow" : "text-muted hover:text-white"
              }`}
            >
              Paper
            </button>
            <button
              onClick={() => onModeChange("live")}
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold transition-all duration-300 sm:px-3.5 sm:text-xs ${
                isLive ? "bg-positive text-bg shadow" : "text-muted hover:text-white"
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

        {/* ── Right: Connection badge + Profile ── */}
        <div className="flex items-center gap-1.5 sm:gap-2.5">
          {/* API health */}
          <div
            className={`flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-medium sm:gap-1.5 sm:px-2.5 ${
              apiConnected
                ? "border-positive/25 bg-positive/5 text-positive"
                : "border-negative/25 bg-negative/5 text-negative"
            }`}
          >
            {apiConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            <span className="hidden sm:block">{apiConnected ? "Connected" : "Offline"}</span>
          </div>

          {/* Profile dropdown */}
          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen((o) => !o)}
              className="flex items-center gap-1.5 rounded-full border border-border bg-surface2 px-2 py-1.5 text-sm transition-colors hover:border-muted/40 sm:gap-2 sm:px-3"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/20 text-[10px] font-bold uppercase text-accent">
                {(portfolioUser ?? "D").charAt(0).toUpperCase()}
              </span>
              <span className="hidden max-w-[100px] truncate text-xs text-muted sm:block">
                {portfolioUser ?? "Demo"}
              </span>
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
                <button
                  onClick={() => { setProfileOpen(false); onSignOut?.(); }}
                  className="flex w-full items-center gap-2.5 px-3.5 py-2 text-xs text-negative transition-colors hover:bg-negative/5"
                >
                  <LogOut className="h-3.5 w-3.5" /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* ── Mobile slide-down menu (absolutely positioned so it overlays, not pushes) ── */}
      {mobileMenuOpen && (
        <div ref={mobileMenuRef} className="animate-slide-up absolute left-0 right-0 top-full border-b border-border bg-surface shadow-2xl md:hidden">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 border-b border-border/40 px-4 py-3 text-sm font-medium transition-colors last:border-b-0 ${
                pathname === href
                  ? "bg-white/5 text-white"
                  : "text-muted hover:bg-white/3 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

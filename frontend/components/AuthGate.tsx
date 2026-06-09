"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { Session } from "@supabase/supabase-js";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";
import { Activity, Shield } from "lucide-react";
import { supabase } from "@/lib/supabase";

// ── Session context ───────────────────────────────────────────────────────────

const SessionContext = createContext<Session | null>(null);

export function useSession(): Session | null {
  return useContext(SessionContext);
}

// ── Auth gate (root wrapper) ──────────────────────────────────────────────────

export default function AuthGate({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // onAuthStateChange fires with INITIAL_SESSION on first setup, giving us
    // the current session state without a separate getSession() call.
    // This eliminates the race where getSession() returns null while a token
    // refresh is in-flight (which would flash the login screen and autofocus
    // the email input, causing the page to scroll to the bottom).
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  // ── Loading splash ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg">
        <div className="flex flex-col items-center gap-3">
          <div className="relative flex h-12 w-12 items-center justify-center">
            <div className="absolute inset-0 animate-ping rounded-full bg-accent/20" />
            <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-accent/10 ring-1 ring-accent/30">
              <Activity className="h-5 w-5 text-accent" strokeWidth={2.5} />
            </div>
          </div>
          <p className="text-xs tracking-widest text-muted">
            INITIALISING SESSION…
          </p>
        </div>
      </div>
    );
  }

  // ── Login gate ──────────────────────────────────────────────────────────────
  if (!session) {
    return <LoginScreen />;
  }

  // ── Authenticated — propagate session via context ───────────────────────────
  return (
    <SessionContext.Provider value={session}>
      {children}
    </SessionContext.Provider>
  );
}

// ── Login screen ──────────────────────────────────────────────────────────────

function LoginScreen() {
  // If the Auth component autofocuses an input (which the browser would scroll
  // to), this snaps the viewport back to the top after mount.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-4 py-12">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-1/2 top-1/3 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/5 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* ── Brand header ── */}
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <div className="relative">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 ring-1 ring-accent/25">
              <Activity className="h-7 w-7 text-accent" strokeWidth={2.5} />
            </div>
            <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-positive text-[8px] font-bold text-bg">
              AI
            </span>
          </div>

          <div>
            <h1 className="text-[26px] font-bold tracking-tight">
              <span className="text-accent">AlphaAgent</span>{" "}
              <span className="text-white">Terminal</span>
            </h1>
            <p className="mt-1.5 text-sm text-muted">
              AI-powered paper trading &mdash; secure login required
            </p>
          </div>

          {/* Security badge */}
          <div className="flex items-center gap-1.5 rounded-full border border-border bg-surface2 px-3 py-1">
            <Shield className="h-3 w-3 text-positive" />
            <span className="text-[11px] text-muted">
              Supabase Auth · JWT-secured · Multi-tenant
            </span>
          </div>
        </div>

        {/* ── Auth form ── */}
        <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-2xl shadow-black/50">
          {/* Card header strip */}
          <div className="border-b border-border/60 bg-surface2/50 px-6 py-3.5">
            <p className="text-xs font-semibold uppercase tracking-widest text-muted">
              Sign in to your account
            </p>
          </div>

          <div className="p-6">
            <Auth
              supabaseClient={supabase}
              appearance={{
                theme: ThemeSupa,
                variables: {
                  default: {
                    colors: {
                      brand: "#FCD535",
                      brandAccent: "#e6bf2e",
                      brandButtonText: "#0B0E11",
                      defaultButtonBackground: "#1E2329",
                      defaultButtonBackgroundHover: "#2B3139",
                      defaultButtonBorder: "#2B3139",
                      defaultButtonText: "#ffffff",
                      dividerBackground: "#2B3139",
                      inputBackground: "#1E2329",
                      inputBorder: "#2B3139",
                      inputBorderHover: "#FCD535",
                      inputBorderFocus: "#FCD535",
                      inputText: "#ffffff",
                      inputLabelText: "#848E9C",
                      inputPlaceholder: "#4a515a",
                      messageText: "#848E9C",
                      messageTextDanger: "#F6465D",
                      anchorTextColor: "#FCD535",
                      anchorTextHoverColor: "#e6bf2e",
                    },
                    borderWidths: {
                      buttonBorderWidth: "1px",
                      inputBorderWidth: "1px",
                    },
                    radii: {
                      borderRadiusButton: "8px",
                      buttonBorderRadius: "8px",
                      inputBorderRadius: "8px",
                    },
                    fontSizes: {
                      baseBodySize: "13px",
                      baseInputSize: "14px",
                      baseLabelSize: "12px",
                      baseButtonSize: "13px",
                    },
                    space: {
                      spaceSmall: "4px",
                      spaceMedium: "8px",
                      spaceLarge: "16px",
                      labelBottomMargin: "6px",
                      anchorBottomMargin: "4px",
                      emailInputSpacing: "4px",
                      socialAuthSpacing: "6px",
                      buttonPadding: "10px 16px",
                      inputPadding: "10px 14px",
                    },
                  },
                },
              }}
              providers={["google"]}
              theme="dark"
              localization={{
                variables: {
                  sign_in: { email_label: "Email address", button_label: "Sign in" },
                  sign_up: { email_label: "Email address", button_label: "Create account" },
                },
              }}
            />
          </div>
        </div>

        {/* Footer note */}
        <p className="mt-5 text-center text-[11px] text-muted/50">
          Paper trading only &mdash; no real funds at risk &mdash;{" "}
          <span className="text-muted/70">AlphaAgent &copy; 2025</span>
        </p>
      </div>
    </div>
  );
}

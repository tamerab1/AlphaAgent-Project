import type { Metadata } from "next";
import "./globals.css";
import AuthGate from "@/components/AuthGate";

export const metadata: Metadata = {
  title: "AlphaAgent — AI Trading Dashboard",
  description: "Two-agent LangGraph paper-trading demo over a SQL portfolio.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg text-white antialiased">
        {/* AuthGate checks for an active Supabase session before rendering the
            dashboard. Shows the login screen if no session is found. */}
        <AuthGate>{children}</AuthGate>
      </body>
    </html>
  );
}

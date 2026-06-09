import type { Metadata } from "next";
import "./globals.css";

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
        {children}
      </body>
    </html>
  );
}

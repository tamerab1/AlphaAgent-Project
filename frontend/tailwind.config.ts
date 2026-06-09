import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg:       "#0B0E11",
        surface:  "#181A20",
        surface2: "#1E2329",
        border:   "#2B3139",
        muted:    "#848E9C",
        accent:   "#FCD535",  // Binance gold — AI branding
        positive: "#0ECB81",  // Binance green
        negative: "#F6465D",  // Binance red
      },
      keyframes: {
        fadeIn:  { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: { "0%": { opacity: "0", transform: "translateY(6px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
      },
      animation: {
        "fade-in":  "fadeIn 0.25s ease-in",
        "slide-up": "slideUp 0.25s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;

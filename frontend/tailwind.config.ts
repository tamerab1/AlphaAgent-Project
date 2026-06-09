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
        // Dark palette tuned to the existing splash page
        bg: "#0d0e15",
        surface: "#1a1c2a",
        border: "#2d3748",
        muted: "#a0aec0",
        accent: "#9061f9",
        positive: "#4ade80",
        negative: "#f87171",
      },
    },
  },
  plugins: [],
};

export default config;

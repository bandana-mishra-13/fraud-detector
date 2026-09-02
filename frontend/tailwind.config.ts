import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#090d16",
        surface: {
          50: "#131a29",
          100: "#182235",
          200: "#1f2c45",
          300: "#2a3b5c",
        },
        border: {
          subtle: "rgba(255, 255, 255, 0.08)",
          glow: "rgba(56, 189, 248, 0.25)",
        },
        primary: {
          DEFAULT: "#0284c7",
          50: "#f0f9ff",
          100: "#e0f2fe",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
        },
        risk: {
          high: "#f43f5e",
          med: "#f59e0b",
          low: "#10b981",
          info: "#06b6d4",
        },
        agent: {
          active: "#8b5cf6",
          plan: "#3b82f6",
          synth: "#10b981",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow": "glow 2s ease-in-out infinite alternate",
      },
      keyframes: {
        glow: {
          "0%": { boxShadow: "0 0 10px rgba(14, 165, 233, 0.2)" },
          "100%": { boxShadow: "0 0 20px rgba(14, 165, 233, 0.6)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;

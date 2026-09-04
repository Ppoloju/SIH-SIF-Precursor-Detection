import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep navy — OIL / industrial primary. Safety semantics stay on
        // red/orange (danger), amber (warning), green (validated) and
        // violet (the single AI accent).
        brand: {
          50: "#eef4fb",
          100: "#dde9f6",
          200: "#c2d6ed",
          300: "#98bade",
          400: "#6796c9",
          500: "#4178ae",
          600: "#2e5f94",
          700: "#254d7b",
          800: "#1d3c60",
          900: "#142b47",
          950: "#0b1a30",
        },
        // Charcoal ink with a cool blue undertone (readable on white and dark).
        ink: {
          DEFAULT: "#1e2836",
          soft: "#3f4c60",
          muted: "#66748a",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(30,58,95,.05), 0 8px 24px -12px rgba(30,58,95,.12)",
        card: "0 2px 4px rgba(30,58,95,.06), 0 20px 44px -16px rgba(30,58,95,.16)",
        lift: "0 4px 6px rgba(30,58,95,.06), 0 24px 48px -12px rgba(30,58,95,.20)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        rise: "rise .45s cubic-bezier(.21,.6,.35,1) both",
        pulseDot: "pulseDot 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;

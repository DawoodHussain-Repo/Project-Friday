import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ["var(--font-heading)", "serif"],
        sans: ["var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      colors: {
        friday: {
          bgTop: "#fbf8f2",
          bgBottom: "#f1ece2",
          paper: "#fffdf9",
          ink: "#23211e",
          muted: "#666157",
          line: "#dfd7c7",
          soft: "#f4efe4",
          brand: "#1e5a96",
          brandSoft: "#eaf1f8",
        },
      },
      keyframes: {
        "rise-in": {
          from: { opacity: "0", transform: "translateY(10px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "float-dot": {
          "0%": { transform: "translateY(0)", opacity: "0.4" },
          "50%": { transform: "translateY(-2px)", opacity: "1" },
          "100%": { transform: "translateY(0)", opacity: "0.4" },
        },
      },
      animation: {
        "rise-in": "rise-in 220ms ease",
        "float-dot": "float-dot 1s infinite ease-in-out",
      },
      boxShadow: {
        panel: "0 14px 40px rgba(45, 40, 30, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;

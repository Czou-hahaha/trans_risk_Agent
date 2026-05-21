import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        sidebar: {
          DEFAULT: "#0f1419",
          foreground: "#e7ecf3",
          muted: "#8b9cb3",
          accent: "#1a2332",
          border: "#243044",
        },
        surface: {
          DEFAULT: "#ffffff",
          muted: "#f6f8fb",
          border: "#e2e8f0",
        },
        brand: {
          DEFAULT: "#2563eb",
          foreground: "#ffffff",
        },
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;

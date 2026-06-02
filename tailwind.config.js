module.exports = {
  darkMode: "class",
  content: [
    "./backend/apps/dashboard/templates/**/*.html",
    "./backend/apps/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          950: "#020617",
        },
        red: {
          950: "#450a0a",
        },
        amber: {
          950: "#451a03",
        },
        emerald: {
          950: "#022c22",
        },
        "brand-dark": "#b91c1c",
        brand: {
          DEFAULT: "#dc2626",
          50: "#fef2f2",
          100: "#fee2e2",
          200: "#fecaca",
          300: "#fca5a5",
          400: "#f87171",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
          800: "#991b1b",
          900: "#7f1d1d",
          950: "#450a0a",
        },
        surface: {
          50: "#ffffff",
          100: "#f8fafc",
          200: "#f1f5f9",
          300: "#e2e8f0",
        },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
        lg: "8px",
        xl: "12px",
      },
      boxShadow: {
        "glass-sm": "0 2px 8px 0 rgba(0, 0, 0, 0.05)",
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.08)",
        card: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        "glow-brand": "0 0 15px rgba(220, 38, 38, 0.2)",
        "glow-red": "0 0 20px rgba(239, 68, 68, 0.3)",
      },
    },
  },
};

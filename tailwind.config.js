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
        "brand-dark": "#1d4ed8",
        brand: {
          DEFAULT: "#2563eb",
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
          950: "#172554",
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
        "glow-brand": "0 0 15px rgba(37, 99, 235, 0.2)",
        "glow-red": "0 0 20px rgba(239, 68, 68, 0.3)",
      },
    },
  },
};

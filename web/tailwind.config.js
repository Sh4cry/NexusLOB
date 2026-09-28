/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#080B11",
        surface: "#0F141E",
        surfaceBorder: "#1B2232",
        surfaceHover: "#161D2B",
        bidGreen: "#00F29D",
        bidBg: "rgba(0, 242, 157, 0.12)",
        askRed: "#FF3B69",
        askBg: "rgba(255, 59, 105, 0.12)",
        brandCyan: "#00C3FF",
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}

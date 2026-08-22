/** Design.md tokens — "Industrial Cyber Command Center". */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        abyss: "#0a0e14",
        panel: "#11161f",
        elevated: "#181f2b",
        cyan1: "#38e0c8",
        glow: "#8ff5e5",
        t1: "#dde4ee",
        t2: "#8b97a8",
        t3: "#56627a",
        ok: "#4ade80",
        warn: "#fbbf24",
        danger: "#f87171",
        info: "#60a5fa",
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};

module.exports = {
  content: ["../backend/templates/**/*.html", "../backend/static/scanner/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        ink: "#050506",
        panel: "#111016",
        neon: "#8b5cf6",
        neonHot: "#e94082",
        crimson: "#ff2d68"
      },
      boxShadow: {
        neon: "0 0 28px rgba(139, 92, 246, .45)",
        crimson: "0 0 30px rgba(255, 45, 104, .38)"
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

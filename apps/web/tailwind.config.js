/** @type {import('tailwindcss').Config} */

// Colors are driven by CSS variables (see src/index.css) so a single `.dark`
// class on <html> re-themes the whole app. Light theme uses the Indian-flag
// palette (white surfaces, saffron + green accents, navy-blue primary).
const withVar = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // primary — the flag's navy blue (Ashoka Chakra blue)
        brand: {
          50: withVar("--brand-50"),
          100: withVar("--brand-100"),
          500: withVar("--brand-500"),
          600: withVar("--brand-600"),
          700: withVar("--brand-700"),
        },
        // neutral surfaces / text (flip between light & dark)
        surface: withVar("--surface"),
        "surface-2": withVar("--surface-2"),
        card: withVar("--card"),
        ink: withVar("--ink"),
        muted: withVar("--muted"),
        subtle: withVar("--subtle"),
        line: withVar("--line"),
        // flag accents
        saffron: withVar("--saffron"),
        flaggreen: withVar("--flag-green"),
      },
    },
  },
  plugins: [],
};

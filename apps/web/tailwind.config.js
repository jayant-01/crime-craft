/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f5f7fb",
          100: "#e8edf6",
          500: "#3b5ba8",
          600: "#2f4988",
          700: "#243766",
        },
      },
    },
  },
  plugins: [],
};

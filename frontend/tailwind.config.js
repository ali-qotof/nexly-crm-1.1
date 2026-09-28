/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Cairo", "system-ui", "sans-serif"] },
      colors: { brand: { 50: "#f1f7ee", 500: "#5b8c3a", 600: "#4a7530", 700: "#3b5e26" } },
    },
  },
  plugins: [],
};

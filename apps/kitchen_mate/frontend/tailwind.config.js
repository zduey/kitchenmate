/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        coral: {
          DEFAULT: "#e85d3d",
          dark: "#d64a2f",
        },
        brown: {
          dark: "#2c2416",
          medium: "#6b5d4f",
        },
        cream: "#fdfbf7",
      },
      fontFamily: {
        serif: ["Crimson Pro", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};

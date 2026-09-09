/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
      colors: {
        obsidian: '#05070B',
        slate: '#0C0F16',
        nebula: {
          violet: '#6b21a8',
          emerald: '#059669',
          indigo: '#3730a3'
        }
      },
      boxShadow: {
        'glow': '0 0 20px rgba(107, 33, 168, 0.4)',
        'floating': '0 25px 50px -12px rgba(0, 0, 0, 0.75)',
      }
    },
  },
  plugins: [],
}

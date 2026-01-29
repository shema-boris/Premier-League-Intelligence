/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Dark theme colors matching mockup
        'pl-dark': '#0d1117',
        'pl-card': '#161b22',
        'pl-border': '#30363d',
        'pl-accent': '#22c55e',
        'pl-accent-orange': '#f97316',
        'pl-text': '#c9d1d9',
        'pl-text-dim': '#8b949e',
      },
    },
  },
  plugins: [],
}

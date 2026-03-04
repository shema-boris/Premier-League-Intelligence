/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'pl-dark': 'var(--color-pl-dark)',
        'pl-card': 'var(--color-pl-card)',
        'pl-border': 'var(--color-pl-border)',
        'pl-accent': 'var(--color-pl-accent)',
        'pl-accent-orange': 'var(--color-pl-accent-orange)',
        'pl-text': 'var(--color-pl-text)',
        'pl-text-dim': 'var(--color-pl-text-dim)',
        'pl-text-bright': 'var(--color-pl-text-bright)',
      },
    },
  },
  plugins: [],
}

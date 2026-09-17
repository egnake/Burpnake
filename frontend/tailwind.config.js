/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0f172a', // slate-900
          800: '#1e293b', // slate-800
          700: '#334155', // slate-700
        },
        primary: {
          500: '#10b981', // emerald-500 (hacker green)
          600: '#059669', // emerald-600
        }
      }
    },
  },
  plugins: [],
}

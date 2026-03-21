/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'oct-deep': '#0A0B0D',
        'oct-deep-light': '#12131A',
        'oct-surface': '#1A1B23',
        'oct-border': '#2A2B35',
        'oct-green': '#00C07A',
        'oct-green-dk': '#007A4D',
        'oct-green-glow': 'rgba(0, 192, 122, 0.3)',
        'oct-text': '#F8F9FA',
        'oct-text-dim': '#9CA3AF',
        'oct-red': '#EF4444',
        'oct-amber': '#F59E0B',
        'oct-blue': '#3B82F6',
      },
      animation: {
        'pulse-green': 'pulse-green 2s infinite',
        'glow-border': 'glow-border 2s infinite',
        'fade-in-up': 'fade-in-up 0.4s ease-out both',
        'shimmer': 'shimmer 1.5s infinite',
      },
      keyframes: {
        'pulse-green': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0, 192, 122, 0.3)' },
          '50%': { boxShadow: '0 0 20px 8px rgba(0, 192, 122, 0.3)' },
        },
        'glow-border': {
          '0%, 100%': { borderColor: '#00C07A', opacity: '0.6' },
          '50%': { borderColor: '#00C07A', opacity: '1' },
        },
        'fade-in-up': {
          'from': { opacity: '0', transform: 'translateY(12px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        }
      }
    },
  },
  plugins: [],
}

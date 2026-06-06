/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        body: ['"DM Sans"', 'sans-serif'],
      },
      colors: {
        sentinel: {
          bg: '#0A0612',
          surface: '#12091F',
          card: '#1A1028',
          border: '#2D1F42',
          primary: '#A855F7',
          secondary: '#EC4899',
          accent: '#F59E0B',
          teal: '#14B8A6',
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          muted: '#9B8AB0',
          text: '#F3EEFA',
        },
      },
      backgroundImage: {
        'grid-pattern': "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%232D1F42' fill-opacity='0.45'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
        'aurora-radial':
          'radial-gradient(ellipse 80% 50% at 20% -10%, rgba(168,85,247,0.22), transparent 55%), radial-gradient(ellipse 60% 40% at 85% 10%, rgba(236,72,153,0.16), transparent 50%), radial-gradient(ellipse 50% 35% at 50% 100%, rgba(245,158,11,0.12), transparent 55%)',
      },
      boxShadow: {
        'glow-violet': '0 0 24px rgba(168, 85, 247, 0.35)',
        'glow-rose': '0 0 24px rgba(236, 72, 153, 0.3)',
        'glow-amber': '0 0 24px rgba(245, 158, 11, 0.3)',
      },
    },
  },
  plugins: [],
}

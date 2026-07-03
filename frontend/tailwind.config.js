/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', 'Inter', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        body:    ['Inter', 'ui-sans-serif', 'sans-serif'],
      },
      colors: {
        yowon: {
          bg:       '#09090B',
          surface:  '#0F0F12',
          card:     '#141418',
          border:   '#1C1C21',
          primary:  '#00E5FF',
          secondary:'#00FFA3',
          accent:   '#7C3AED',
          teal:     '#00FFA3',
          success:  '#10B981',
          warning:  '#F59E0B',
          danger:   '#EF4444',
          muted:    '#71717A',
          dim:      '#52525B',
          text:     '#F4F4F5',
        },
      },
      backgroundImage: {
        'grid-pattern': "url(\"data:image/svg+xml,%3Csvg width='52' height='52' viewBox='0 0 52 52' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none'%3E%3Cpath stroke='rgba(0,229,255,0.06)' d='M0 0h52M0 26h52'/%3E%3Cpath stroke='rgba(0,229,255,0.06)' d='M0 0v52M26 0v52'/%3E%3C/g%3E%3C/svg%3E\")",
        'aurora-radial':
          'radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0,229,255,0.16), transparent 55%), radial-gradient(ellipse 60% 40% at 85% 10%, rgba(0,255,163,0.10), transparent 50%), radial-gradient(ellipse 50% 35% at 50% 100%, rgba(124,58,237,0.14), transparent 55%)',
        'glass-gradient':
          'linear-gradient(135deg, rgba(255,255,255,0.038) 0%, rgba(255,255,255,0.018) 100%)',
      },
      boxShadow: {
        'glow-cyan':    '0 0 24px rgba(0, 229, 255, 0.28)',
        'glow-emerald': '0 0 24px rgba(0, 255, 163, 0.22)',
        'glow-violet':  '0 0 24px rgba(124,  58, 237, 0.30)',
        'glow-red':     '0 0 24px rgba(239,  68,  68, 0.25)',
        'glass':        '0 20px 60px rgba(0,0,0,0.45), 0 4px 20px rgba(0,0,0,0.25)',
        'glass-hover':  '0 24px 70px rgba(0,0,0,0.50), 0 6px 24px rgba(0,0,0,0.30)',
      },
      animation: {
        'pulse-slow': 'pulse-slow 4s ease-in-out infinite',
        'float':      'float 4s ease-in-out infinite',
        'gradient':   'gradient-shift 7s ease infinite',
        'scan':       'scan 3s linear infinite',
        'shimmer':    'shimmer 2s infinite',
      },
      keyframes: {
        'pulse-slow': {
          '0%, 100%': { opacity: '0.35' },
          '50%':      { opacity: '0.75' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-6px)' },
        },
        'gradient-shift': {
          '0%':   { backgroundPosition: '0% 50%' },
          '50%':  { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
        scan: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
      },
    },
  },
  plugins: [],
}

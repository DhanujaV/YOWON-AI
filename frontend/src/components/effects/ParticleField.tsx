import { useMemo } from 'react'
import { motion } from 'framer-motion'

interface Particle {
  id: number
  x: number
  y: number
  size: number
  duration: number
  delay: number
  hue: 'violet' | 'rose' | 'amber'
}

const HUE_STYLES = {
  violet: { bg: 'bg-violet-400/35', shadow: '0 0 6px rgba(168,85,247,0.55)' },
  rose: { bg: 'bg-pink-400/35', shadow: '0 0 6px rgba(236,72,153,0.5)' },
  amber: { bg: 'bg-amber-400/30', shadow: '0 0 6px rgba(245,158,11,0.45)' },
}

export default function ParticleField({ count = 40 }: { count?: number }) {
  const particles = useMemo<Particle[]>(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 2 + 0.5,
        duration: Math.random() * 20 + 15,
        delay: Math.random() * 5,
        hue: (['violet', 'rose', 'amber'] as const)[i % 3],
      })),
    [count],
  )

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
      {particles.map(p => {
        const style = HUE_STYLES[p.hue]
        return (
          <motion.div
            key={p.id}
            className={`absolute rounded-full ${style.bg}`}
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              boxShadow: style.shadow,
            }}
            animate={{
              y: [0, -30, 0],
              opacity: [0.2, 0.8, 0.2],
            }}
            transition={{
              duration: p.duration,
              delay: p.delay,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )
      })}
    </div>
  )
}

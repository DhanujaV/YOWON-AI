import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Gauge } from 'lucide-react'
import { scoreColor } from '../../utils/reportParser'

interface ReadinessGaugeProps {
  score: number
}

export default function ReadinessGauge({ score }: ReadinessGaugeProps) {
  const [animated, setAnimated] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setAnimated(score), 400)
    return () => clearTimeout(t)
  }, [score])

  const color = scoreColor(score)
  const rotation = (animated / 100) * 180 - 90

  return (
    <div className="glass-card p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <Gauge size={16} className="text-sentinel-accent" />
        <span className="text-xs font-mono text-sentinel-muted uppercase tracking-widest">
          Deployment Readiness
        </span>
      </div>

      <div className="relative flex-1 flex items-center justify-center min-h-[140px]">
        <svg viewBox="0 0 200 120" className="w-full max-w-[220px]">
          {/* Gauge arc background */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#1E2D45"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Gauge arc fill */}
          <motion.path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray="251"
            initial={{ strokeDashoffset: 251 }}
            animate={{ strokeDashoffset: 251 - (animated / 100) * 251 }}
            transition={{ duration: 2, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 6px ${color}80)` }}
          />
          {/* Tick marks */}
          {[0, 25, 50, 75, 100].map((tick, i) => {
            const angle = ((tick / 100) * 180 - 90) * (Math.PI / 180)
            const x1 = 100 + 65 * Math.cos(angle)
            const y1 = 100 + 65 * Math.sin(angle)
            const x2 = 100 + 72 * Math.cos(angle)
            const y2 = 100 + 72 * Math.sin(angle)
            return (
              <line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="#64748B"
                strokeWidth="1"
              />
            )
          })}
          {/* Needle */}
          <motion.g
            style={{ transformOrigin: '100px 100px' }}
            animate={{ rotate: rotation }}
            transition={{ duration: 2, ease: 'easeOut' }}
          >
            <line x1="100" y1="100" x2="100" y2="35" stroke={color} strokeWidth="2" />
            <circle cx="100" cy="100" r="6" fill={color} />
          </motion.g>
          <text x="100" y="85" textAnchor="middle" fill={color} fontSize="22" fontWeight="700" fontFamily="Space Grotesk">
            {Math.round(animated)}
          </text>
        </svg>
      </div>

      <p className="text-center text-xs text-sentinel-muted font-mono mt-1">
        COCKPIT READINESS INDEX
      </p>
    </div>
  )
}

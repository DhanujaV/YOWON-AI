import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { scoreColor } from '../utils/reportParser'

interface ScoreRingProps {
  score: number
  size?: number
  label?: string
}

/**
 * Premium animated SVG score ring.
 * - Gradient stroke via linearGradient SVG element
 * - Glow shadow that pulses
 * - Animated strokeDashoffset transition
 * - Space Grotesk typography for number
 */
export default function ScoreRing({ score, size = 160, label }: ScoreRingProps) {
  const [animated, setAnimated] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setAnimated(score), 200)
    return () => clearTimeout(t)
  }, [score])

  const radius       = (size - 18) / 2
  const circumference = 2 * Math.PI * radius
  const offset       = circumference - (animated / 100) * circumference
  const color        = scoreColor(score)
  const gradientId   = `score-grad-${size}`

  // Pick gradient colors based on score
  const gradEnd = score >= 80 ? '#00FFA3' : score >= 60 ? '#F59E0B' : '#EF4444'

  return (
    <motion.div
      className="flex flex-col items-center gap-2"
      initial={{ opacity: 0, scale: 0.88 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
    >
      <div className="relative">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          aria-label={`Score: ${Math.round(score)} out of 100`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%"   stopColor={color}   />
              <stop offset="100%" stopColor={gradEnd} />
            </linearGradient>
          </defs>

          {/* Track */}
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={10}
          />

          {/* Progress arc */}
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none"
            stroke={`url(#${gradientId})`}
            strokeWidth={10}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="score-ring"
            style={{
              filter: `drop-shadow(0 0 10px ${color}70)`,
              transition: 'stroke-dashoffset 1.8s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />

          {/* Score text */}
          <text
            x={size / 2} y={size / 2 - 5}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={color}
            fontSize={size * 0.23}
            fontWeight="800"
            fontFamily="Space Grotesk, sans-serif"
            letterSpacing="-1"
          >
            {Math.round(animated)}
          </text>

          {/* /100 label */}
          <text
            x={size / 2} y={size / 2 + size * 0.145}
            textAnchor="middle"
            fill="#52525B"
            fontSize={size * 0.085}
            fontWeight="600"
            fontFamily="JetBrains Mono, monospace"
            letterSpacing="1"
          >
            / 100
          </text>
        </svg>

        {/* Glow pulse */}
        <motion.div
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{ boxShadow: `0 0 30px ${color}28` }}
          animate={{ opacity: [0.25, 0.55, 0.25] }}
          transition={{ duration: 3.5, repeat: Infinity }}
        />
      </div>

      {label && (
        <span className="text-[10px] font-mono uppercase tracking-[0.25em] text-yowon-muted">
          {label}
        </span>
      )}
    </motion.div>
  )
}

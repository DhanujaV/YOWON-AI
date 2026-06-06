import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { scoreColor } from '../utils/reportParser'

interface ScoreRingProps {
  score: number
  size?: number
  label?: string
}

export default function ScoreRing({ score, size = 160, label }: ScoreRingProps) {
  const [animatedScore, setAnimatedScore] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 200)
    return () => clearTimeout(timer)
  }, [score])

  const radius = (size - 20) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (animatedScore / 100) * circumference
  const color = scoreColor(score)

  return (
    <motion.div
      className="flex flex-col items-center gap-3"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6 }}
    >
      <div className="relative">
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1E2D45"
            strokeWidth={10}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={10}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="score-ring"
            style={{
              filter: `drop-shadow(0 0 12px ${color}80)`,
              transition: 'stroke-dashoffset 2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
          <text
            x={size / 2}
            y={size / 2 - 6}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={color}
            fontSize={size * 0.24}
            fontWeight="700"
            fontFamily="Space Grotesk"
          >
            {Math.round(animatedScore)}
          </text>
          <text
            x={size / 2}
            y={size / 2 + size * 0.14}
            textAnchor="middle"
            fill="#64748B"
            fontSize={size * 0.09}
            fontFamily="DM Sans"
          >
            / 100
          </text>
        </svg>
        <motion.div
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{ boxShadow: `0 0 30px ${color}30` }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 3, repeat: Infinity }}
        />
      </div>
      {label && (
        <span className="text-xs text-sentinel-muted font-display font-medium tracking-widest uppercase">
          {label}
        </span>
      )}
    </motion.div>
  )
}

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Brain } from 'lucide-react'

interface ConfidenceMeterProps {
  value: number
  label?: string
}

export default function ConfidenceMeter({ value, label = 'AI Confidence' }: ConfidenceMeterProps) {
  const [animated, setAnimated] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setAnimated(value), 300)
    return () => clearTimeout(t)
  }, [value])

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <Brain size={16} className="text-sentinel-accent" />
        <span className="text-xs font-mono text-sentinel-muted uppercase tracking-widest">
          {label}
        </span>
      </div>
      <div className="relative h-3 rounded-full bg-sentinel-border overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-sentinel-primary via-sentinel-accent to-amber-300"
          initial={{ width: 0 }}
          animate={{ width: `${animated}%` }}
          transition={{ duration: 1.8, ease: 'easeOut' }}
          style={{ boxShadow: '0 0 12px rgba(6,182,212,0.5)' }}
        />
      </div>
      <div className="flex justify-between mt-2">
        <span className="text-2xl font-display font-bold text-amber-300">{animated}%</span>
        <span className="text-xs text-sentinel-muted self-end">Neural certainty index</span>
      </div>
    </div>
  )
}

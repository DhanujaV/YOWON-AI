import { motion } from 'framer-motion'
import { Users } from 'lucide-react'

interface AgentConsensusProps {
  score: number
}

export default function AgentConsensus({ score }: AgentConsensusProps) {
  const segments = 10

  return (
    <div className="glass-card p-5">
      <div className="flex items-center gap-2 mb-4">
        <Users size={16} className="text-sentinel-primary" />
        <span className="text-xs font-mono text-sentinel-muted uppercase tracking-widest">
          Agent Consensus
        </span>
      </div>

      <div className="flex gap-1 mb-3">
        {Array.from({ length: segments }).map((_, i) => {
          const filled = i < Math.round((score / 100) * segments)
          return (
            <motion.div
              key={i}
              className="flex-1 h-8 rounded-sm"
              initial={{ scaleY: 0 }}
              animate={{
                scaleY: 1,
                background: filled
                  ? `linear-gradient(180deg, #A855F7, #EC4899)`
                  : '#1E2D45',
              }}
              transition={{ delay: i * 0.08, duration: 0.4 }}
              style={{
                opacity: filled ? 0.7 + (i / segments) * 0.3 : 0.4,
                boxShadow: filled ? '0 0 8px rgba(6,182,212,0.3)' : 'none',
              }}
            />
          )
        })}
      </div>

      <div className="flex justify-between items-end">
        <div>
          <motion.span
            className="text-3xl font-display font-bold text-sentinel-text"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            {score}%
          </motion.span>
          <p className="text-xs text-sentinel-muted mt-0.5">Inter-agent agreement</p>
        </div>
        <p className="text-xs font-mono text-emerald-400">
          {score >= 85 ? 'HIGH ALIGNMENT' : score >= 70 ? 'MODERATE' : 'DIVERGENT'}
        </p>
      </div>
    </div>
  )
}

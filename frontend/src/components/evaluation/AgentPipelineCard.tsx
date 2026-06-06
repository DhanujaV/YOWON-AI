import { motion } from 'framer-motion'
import { CheckCircle2, Loader2, Circle } from 'lucide-react'
import type { AgentStatus } from '../../types'
import type { ElementType } from 'react'

interface AgentPipelineCardProps {
  label: string
  description: string
  status: AgentStatus
  index: number
  icon: ElementType
  color: string
}

export default function AgentPipelineCard({
  label,
  description,
  status,
  index,
  icon: Icon,
  color,
}: AgentPipelineCardProps) {
  return (
    <motion.div
      className={`relative flex items-start gap-4 p-4 rounded-xl border transition-all duration-500 ${
        status === 'running'
          ? 'glass-card border-violet-500/30 shadow-glow-violet'
          : status === 'completed'
            ? 'bg-white/[0.02] border-white/5 opacity-80'
            : 'bg-transparent border-transparent opacity-40'
      }`}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: status === 'waiting' ? 0.4 : 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div
          className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 border ${
            status === 'completed'
              ? 'bg-emerald-500/15 border-emerald-500/30'
              : status === 'running'
                ? 'bg-violet-500/15 border-violet-400/40'
                : 'bg-sentinel-surface border-sentinel-border'
          }`}
        >
          {status === 'completed' ? (
            <CheckCircle2 size={16} className="text-emerald-400" />
          ) : status === 'running' ? (
            <Loader2 size={16} className="text-violet-300 animate-spin" />
          ) : (
            <Circle size={14} className="text-sentinel-muted" />
          )}
        </div>
        {index < 9 && (
          <div
            className={`w-px h-6 mt-1 ${
              status === 'completed' ? 'bg-emerald-500/30' : 'bg-sentinel-border'
            }`}
          />
        )}
      </div>

      <div className="flex-1 min-w-0 pt-1">
        <div className="flex items-center gap-2">
          <Icon size={14} style={{ color }} />
          <p
            className={`text-sm font-display font-semibold ${
              status === 'running' ? 'text-violet-200' : 'text-sentinel-text'
            }`}
          >
            {label}
          </p>
          {status === 'running' && (
            <motion.span
              className="text-[10px] font-mono text-violet-400 uppercase tracking-widest"
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              Running
            </motion.span>
          )}
          {status === 'completed' && (
            <span className="text-[10px] font-mono text-emerald-400/80 uppercase">Done</span>
          )}
          {status === 'waiting' && (
            <span className="text-[10px] font-mono text-sentinel-muted uppercase">Waiting</span>
          )}
        </div>
        {(status === 'running' || status === 'completed') && (
          <p className="text-xs text-sentinel-muted mt-1">{description}</p>
        )}
      </div>

      {status === 'running' && (
        <motion.div
          className="absolute inset-0 rounded-xl pointer-events-none"
          style={{
            background: `linear-gradient(90deg, transparent, ${color}08, transparent)`,
          }}
          animate={{ x: ['-100%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
      )}
    </motion.div>
  )
}

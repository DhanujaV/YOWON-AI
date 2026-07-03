import { motion } from 'framer-motion'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import type { ElementType } from 'react'
import type { AgentStatus } from '../../types'

interface AgentPipelineCardProps {
  label: string
  description: string
  status: AgentStatus
  index: number
  icon: ElementType
  color: string
}

const STATUS_CONFIG: Record<AgentStatus, {
  border: string; bg: string; labelColor: string; badge: string;
}> = {
  completed: {
    border: 'border-emerald-500/25',
    bg:     'bg-emerald-500/[0.05]',
    labelColor: 'text-white',
    badge:  'text-emerald-400',
  },
  running: {
    border: 'border-cyan-300/35',
    bg:     'bg-cyan-300/[0.06]',
    labelColor: 'text-cyan-100',
    badge:  'text-cyan-300',
  },
  failed: {
    border: 'border-red-400/30',
    bg:     'bg-red-400/[0.05]',
    labelColor: 'text-red-300',
    badge:  'text-red-400',
  },
  waiting: {
    border: 'border-transparent',
    bg:     'bg-transparent',
    labelColor: 'text-yowon-muted',
    badge:  'text-yowon-muted',
  },
}

export default function AgentPipelineCard({
  label, description, status, index, icon: Icon, color,
}: AgentPipelineCardProps) {
  const cfg = STATUS_CONFIG[status]

  return (
    <motion.div
      className={`relative flex items-start gap-3.5 p-3.5 rounded-xl border transition-all duration-300 ${cfg.border} ${cfg.bg}`}
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: status === 'waiting' ? 0.38 : 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      {/* Shimmer sweep when running */}
      {status === 'running' && (
        <motion.div
          className="absolute inset-0 rounded-xl pointer-events-none overflow-hidden"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        >
          <motion.div
            className="absolute inset-y-0 w-1/3 blur-xl"
            style={{ background: `linear-gradient(90deg, transparent, ${color}18, transparent)` }}
            animate={{ left: ['-35%', '115%'] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
          />
        </motion.div>
      )}

      {/* Timeline column */}
      <div className="flex flex-col items-center shrink-0">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border transition-all ${
          status === 'completed' ? 'bg-emerald-500/15 border-emerald-500/30' :
          status === 'running'   ? 'border-cyan-300/40 shadow-[0_0_12px_rgba(0,229,255,0.25)]' :
          status === 'failed'    ? 'bg-red-400/10 border-red-400/30' :
          'border-white/[0.08] bg-white/[0.03]'
        }`}
          style={status === 'running' ? { background: `${color}18` } : {}}
        >
          {status === 'completed' && <CheckCircle2 size={15} className="text-emerald-400" />}
          {status === 'running'   && <Loader2 size={14} className="animate-spin" style={{ color }} />}
          {status === 'failed'    && <XCircle size={15} className="text-red-400" />}
          {status === 'waiting'   && <Icon size={13} className="text-yowon-muted" />}
        </div>
        {index < 6 && (
          <div className={`w-px mt-1 flex-1 min-h-[14px] ${
            status === 'completed' ? 'bg-emerald-500/25' : 'bg-white/[0.05]'
          }`} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        <div className="flex items-center gap-2">
          <Icon size={12} style={{ color: status === 'waiting' ? '#52525B' : color }} />
          <span className={`text-xs font-semibold ${cfg.labelColor}`}>{label}</span>

          {status === 'running' && (
            <motion.span
              className="ml-auto text-[9px] font-mono font-bold uppercase tracking-[0.2em]"
              style={{ color }}
              animate={{ opacity: [1, 0.35, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            >
              Running
            </motion.span>
          )}
          {status === 'completed' && (
            <span className="ml-auto text-[9px] font-mono font-bold text-emerald-400 uppercase tracking-[0.15em]">Done</span>
          )}
        </div>

        {(status === 'running' || status === 'completed') && (
          <p className="text-[11px] text-yowon-muted mt-1 leading-relaxed">{description}</p>
        )}
      </div>
    </motion.div>
  )
}

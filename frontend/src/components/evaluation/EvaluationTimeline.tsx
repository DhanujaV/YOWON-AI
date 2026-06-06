import { motion } from 'framer-motion'
import { CheckCircle, Loader2, XCircle } from 'lucide-react'
import type { ProgressEvent } from '../../types'

const AGENT_LABELS: Record<string, string> = {
  coordinator: 'Coordinator',
  brief: 'Coordinator',
  technical: 'Engineering',
  security: 'Security',
  presentation: 'Presentation',
  innovation: 'Innovation',
  risk: 'Risk',
  scoring: 'Score Engine',
  chief: 'Chief Evaluator',
}

interface EvaluationTimelineProps {
  events?: ProgressEvent[]
  elapsedSeconds?: number
}

export default function EvaluationTimeline({ events = [], elapsedSeconds = 0 }: EvaluationTimelineProps) {
  const formatTime = (ts: number) => {
    const offset = Math.max(0, Math.round(ts - (events[0]?.ts ?? ts)))
    const m = Math.floor(offset / 60)
    const s = offset % 60
    return m > 0 ? `${m}:${s.toString().padStart(2, '0')}` : `${s}s`
  }

  const displayEvents = events.filter(e => e.type === 'agent_start' || e.type === 'agent_complete')

  if (displayEvents.length === 0) {
    return (
      <div className="glass-card p-4">
        <h2 className="text-xs font-mono text-sentinel-muted uppercase tracking-[0.2em] mb-3">
          Live Timeline
        </h2>
        <p className="text-xs text-sentinel-muted font-mono">Awaiting agent events...</p>
      </div>
    )
  }

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-mono text-sentinel-muted uppercase tracking-[0.2em]">
          Live Timeline
        </h2>
        <span className="text-[10px] font-mono text-violet-400/80">
          {elapsedSeconds}s elapsed
        </span>
      </div>
      <div className="space-y-2 max-h-40 overflow-y-auto">
        {displayEvents.slice(-12).map((event, i) => {
          const label = AGENT_LABELS[event.agent] ?? event.agent
          const isComplete = event.type === 'agent_complete'
          const isFailed = isComplete && !!event.error

          return (
            <motion.div
              key={`${event.agent}-${event.type}-${i}`}
              className="flex items-center gap-2 text-[11px] font-mono"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
            >
              {isFailed ? (
                <XCircle size={12} className="text-red-400 shrink-0" />
              ) : isComplete ? (
                <CheckCircle size={12} className="text-emerald-400 shrink-0" />
              ) : (
                <Loader2 size={12} className="text-violet-400 shrink-0 animate-spin" />
              )}
              <span className="text-sentinel-muted w-20 shrink-0">{formatTime(event.ts)}</span>
              <span className={isFailed ? 'text-red-300/80' : 'text-violet-200/80'}>
                {label}
                {isComplete && event.duration_sec != null && (
                  <span className="text-sentinel-muted ml-1">({event.duration_sec}s)</span>
                )}
                {!isComplete && event.model && (
                  <span className="text-sentinel-muted ml-1 text-[10px]">{event.model}</span>
                )}
              </span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

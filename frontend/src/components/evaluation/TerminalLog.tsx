import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal } from 'lucide-react'

interface TerminalLogProps {
  logs?: string[]
}

export default function TerminalLog({ logs }: TerminalLogProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const displayLogs = logs && logs.length > 0 ? logs.slice(-25) : ['[SYS] Waiting for agent telemetry...']

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: 'smooth' })
  }, [displayLogs])

  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-2 mb-3">
        <Terminal size={14} className="text-violet-400" />
        <h2 className="text-xs font-mono text-sentinel-muted uppercase tracking-[0.2em]">
          Live Agent Log
        </h2>
        <span className="ml-auto text-[10px] font-mono text-emerald-400/60">SSE STREAM</span>
      </div>
      <div
        ref={containerRef}
        className="bg-black/50 rounded-lg p-3 h-52 overflow-y-auto font-mono text-[11px] leading-relaxed border border-violet-500/10"
      >
        <AnimatePresence>
          {displayLogs.map((log, i) => {
            const isError = log.includes('[ERR]') || log.includes('Failed') || log.includes('Fallback')
            const isComplete = log.includes('Completed') || log.includes('complete')
            return (
              <motion.div
                key={`${log}-${i}`}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`mb-1 ${
                  isError ? 'text-red-300/90' : isComplete ? 'text-emerald-300/80' : 'text-violet-300/80'
                }`}
              >
                <span className="text-emerald-400/50">{'>'}</span> {log}
              </motion.div>
            )
          })}
        </AnimatePresence>
        <motion.span
          className="inline-block w-2 h-3 bg-violet-400/80 ml-1"
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        />
      </div>
    </div>
  )
}

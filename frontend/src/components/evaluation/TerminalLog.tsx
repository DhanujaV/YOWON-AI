import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal } from 'lucide-react'

interface TerminalLogProps {
  logs?: string[]
}

function classifyLog(log: string) {
  if (log.includes('[ERR]') || log.includes('Failed') || log.includes('Error') || log.includes('Fallback'))
    return { color: 'text-red-400/90',     prompt: '✕' }
  if (log.includes('Completed') || log.includes('complete') || log.includes('[OK]') || log.includes('Done'))
    return { color: 'text-emerald-400/85', prompt: '✓' }
  if (log.includes('[SYS]') || log.includes('[WARN]'))
    return { color: 'text-amber-400/75',   prompt: '⚠' }
  return { color: 'text-cyan-300/70',      prompt: '›' }
}

export default function TerminalLog({ logs }: TerminalLogProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const displayLogs  = logs && logs.length > 0
    ? logs.slice(-25)
    : ['[SYS] Waiting for agent telemetry...']

  useEffect(() => {
    containerRef.current?.scrollTo({
      top: containerRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [displayLogs])

  return (
    <div className="glass-card !p-0 overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.025]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <Terminal size={12} className="text-yowon-muted ml-2" />
        <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em] flex-1">
          Live Agent Log
        </span>
        <span className="text-[9px] font-mono text-emerald-400/60 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
          SSE
        </span>
      </div>

      {/* Log body */}
      <div
        ref={containerRef}
        className="px-4 py-3 h-52 overflow-y-auto font-mono text-[11px] leading-relaxed scrollbar-thin"
        style={{ background: 'rgba(0,0,0,0.45)' }}
      >
        <AnimatePresence initial={false}>
          {displayLogs.map((log, i) => {
            const { color, prompt } = classifyLog(log)
            return (
              <motion.div
                key={`${log}-${i}`}
                className={`flex gap-2 mb-1.5 ${color}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15 }}
              >
                <span className="shrink-0 text-yowon-muted/40 select-none">{prompt}</span>
                <span className="break-all">{log}</span>
              </motion.div>
            )
          })}
        </AnimatePresence>
        {/* Blinking cursor */}
        <motion.span
          className="inline-block w-1.5 h-3.5 bg-cyan-300/70 ml-1 align-middle"
          animate={{ opacity: [1, 0, 1] }}
          transition={{ duration: 0.9, repeat: Infinity }}
        />
      </div>
    </div>
  )
}

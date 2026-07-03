import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import VerdictBadge from '../VerdictBadge'
import type { VerdictType } from '../../types'

interface VerdictRevealProps {
  verdict: VerdictType | string
  onRevealed?: () => void
}

const TELEMETRY_PHASES = [
  'Resolving coordinator briefing...',
  'Cross-examining Forge architecture models...',
  'Checking Sentinel dependency trees against OWASP database...',
  'Analyzing Showcase slide deck narrative structures...',
  'Guardian forecasting operations failure risk limit bounds...',
  'YOWON Prime synthesizing verdict consensus matrices...',
]

export default function VerdictReveal({ verdict, onRevealed }: VerdictRevealProps) {
  const [phase, setPhase] = useState<'scanning' | 'revealed'>('scanning')
  const [telemetryIndex, setTelemetryIndex] = useState(0)

  useEffect(() => {
    // Scroll telemetry texts
    const interval = setInterval(() => {
      setTelemetryIndex((prev) => (prev + 1) % TELEMETRY_PHASES.length)
    }, 450)

    const t = setTimeout(() => {
      setPhase('revealed')
      onRevealed?.()
      clearInterval(interval)
    }, 2900)

    return () => {
      clearTimeout(t)
      clearInterval(interval)
    }
  }, [onRevealed])

  return (
    <div className="relative py-12 flex flex-col items-center justify-center overflow-hidden">
      
      {/* Background sweep lights during scanning */}
      <AnimatePresence>
        {phase === 'scanning' && (
          <motion.div
            className="absolute inset-0 pointer-events-none -z-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.15 }}
            exit={{ opacity: 0 }}
          >
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full bg-gradient-to-r from-cyan-400 via-emerald-400 to-violet-500 blur-[80px] animate-[spin_6s_linear_infinite]" />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {phase === 'scanning' ? (
          <motion.div
            key="scan"
            className="text-center w-full max-w-md px-4"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            <div className="cyber-glow-card">
              <div className="cyber-glow-inner !p-6 flex flex-col items-center">
                
                {/* Active Scanning Pulse */}
                <div className="relative w-16 h-16 mb-5">
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-cyan-400"
                    animate={{ scale: [1, 1.8, 1], opacity: [0.8, 0, 0.8] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
                  />
                  <motion.div
                    className="absolute inset-2 rounded-full border border-dashed border-emerald-400"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
                  />
                  <div className="absolute inset-4 rounded-full bg-[#00E5FF]/20 flex items-center justify-center">
                    <span className="w-2.5 h-2.5 rounded-full bg-[#00FFA3] animate-ping" />
                  </div>
                </div>

                <h3 className="font-display text-base font-bold text-white tracking-wider mb-2">
                  Jury Deliberation Analysis
                </h3>
                
                {/* Telemetry stream text */}
                <div className="h-6 w-full flex items-center justify-center overflow-hidden">
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={telemetryIndex}
                      initial={{ y: 15, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: -15, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="text-[10px] font-mono text-cyan-300 uppercase tracking-widest truncate max-w-full px-2"
                    >
                      {TELEMETRY_PHASES[telemetryIndex]}
                    </motion.p>
                  </AnimatePresence>
                </div>

                {/* Animated status scanning bar */}
                <div className="w-full h-1 bg-white/[0.06] rounded-full overflow-hidden mt-4">
                  <motion.div
                    className="h-full bg-gradient-to-r from-cyan-400 to-[#00FFA3]"
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2.8, ease: 'linear' }}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="verdict"
            initial={{ opacity: 0, scale: 0.4 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 220, damping: 18 }}
            className="text-center relative"
          >
            {/* Dramatic light ring burst behind verdict */}
            <motion.div
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 blur-[60px] pointer-events-none -z-10"
              initial={{ scale: 0.1 }}
              animate={{ scale: [0.1, 1.4, 1.2] }}
              transition={{ duration: 0.8 }}
            />
            
            <p className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.3em] mb-4">
              Jury Council Verdict Rendered
            </p>
            <VerdictBadge verdict={verdict} large animated />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

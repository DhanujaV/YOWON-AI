import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import VerdictBadge from '../VerdictBadge'
import type { VerdictType } from '../../types'

interface VerdictRevealProps {
  verdict: VerdictType | string
  onRevealed?: () => void
}

export default function VerdictReveal({ verdict, onRevealed }: VerdictRevealProps) {
  const [phase, setPhase] = useState<'scanning' | 'revealed'>('scanning')

  useEffect(() => {
    const t = setTimeout(() => {
      setPhase('revealed')
      onRevealed?.()
    }, 2800)
    return () => clearTimeout(t)
  }, [onRevealed])

  return (
    <div className="relative py-8">
      <AnimatePresence mode="wait">
        {phase === 'scanning' ? (
          <motion.div
            key="scan"
            className="text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            <motion.div
              className="inline-flex items-center gap-3 px-6 py-4 rounded-xl glass-card border border-violet-500/20"
              animate={{
                boxShadow: [
                  '0 0 20px rgba(6,182,212,0.1)',
                  '0 0 40px rgba(6,182,212,0.3)',
                  '0 0 20px rgba(6,182,212,0.1)',
                ],
              }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <motion.div
                className="w-3 h-3 rounded-full bg-violet-400"
                animate={{ scale: [1, 1.5, 1], opacity: [1, 0.5, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
              <span className="font-display font-semibold text-violet-200 tracking-wide">
                AI Jury Deliberating Final Verdict...
              </span>
            </motion.div>
            <motion.p
              className="text-sm text-sentinel-muted mt-4 font-mono"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              Cross-referencing 10 specialist agent reports
            </motion.p>
          </motion.div>
        ) : (
          <motion.div
            key="verdict"
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            className="text-center"
          >
            <p className="text-xs font-mono text-sentinel-muted uppercase tracking-[0.3em] mb-4">
              Deployment Verdict
            </p>
            <VerdictBadge verdict={verdict} large animated />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

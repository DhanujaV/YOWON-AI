import { motion } from 'framer-motion'
import {
  Cpu, Shield, Presentation, Lightbulb, Globe, Gavel, Brain,
} from 'lucide-react'
import type { AgentStatus } from '../../types'

const JURY_AGENTS = [
  { icon: Brain, label: 'Brief', angle: 0 },
  { icon: Cpu, label: 'Forge', angle: 51 },
  { icon: Shield, label: 'Sentinel', angle: 103 },
  { icon: Presentation, label: 'Showcase', angle: 154 },
  { icon: Lightbulb, label: 'Visionary', angle: 206 },
  { icon: Globe, label: 'Guardian', angle: 257 },
  { icon: Gavel, label: 'Prime', angle: 309 },
]

interface JuryChamberProps {
  activeIndex: number
  statuses: AgentStatus[]
}

export default function JuryChamber({ activeIndex, statuses }: JuryChamberProps) {
  const radius = 120
  const centerX = 150
  const centerY = 150

  return (
    <div className="relative w-[300px] h-[300px] mx-auto">
      <div className="absolute inset-0 rounded-full border border-violet-500/10" />
      <div className="absolute inset-4 rounded-full border border-violet-500/5" />
      <div className="absolute inset-8 rounded-full border border-dashed border-violet-500/10" />

      <motion.div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-violet-500/10 border border-violet-500/30 flex items-center justify-center"
        animate={{
          boxShadow: [
            '0 0 15px rgba(6,182,212,0.2)',
            '0 0 30px rgba(6,182,212,0.4)',
            '0 0 15px rgba(6,182,212,0.2)',
          ],
        }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <span className="text-[10px] font-mono text-violet-300">JURY</span>
      </motion.div>

      {JURY_AGENTS.map((agent, i) => {
        const angleRad = ((agent.angle - 90) * Math.PI) / 180
        const x = centerX + radius * Math.cos(angleRad) - 20
        const y = centerY + radius * Math.sin(angleRad) - 20
        const status = statuses[i] || 'waiting'
        const isActive = i === activeIndex
        const Icon = agent.icon

        return (
          <motion.div
            key={agent.label}
            className="absolute w-10 h-10 flex flex-col items-center"
            style={{ left: x, top: y }}
            animate={isActive ? { scale: [1, 1.15, 1] } : { scale: 1 }}
            transition={{ duration: 1.5, repeat: isActive ? Infinity : 0 }}
          >
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center border transition-colors ${
                status === 'completed'
                  ? 'bg-emerald-500/20 border-emerald-500/40'
                  : status === 'running'
                    ? 'bg-violet-500/20 border-violet-400/60'
                    : 'bg-white/5 border-white/10'
              }`}
            >
              <Icon
                size={16}
                className={
                  status === 'completed'
                    ? 'text-emerald-400'
                    : status === 'running'
                      ? 'text-violet-300'
                      : 'text-yowon-muted'
                }
              />
            </div>
            <span className="text-[8px] font-mono text-yowon-muted mt-1 whitespace-nowrap">
              {agent.label}
            </span>
          </motion.div>
        )
      })}
    </div>
  )
}

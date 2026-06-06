import { motion } from 'framer-motion'
import {
  Cpu, Shield, Presentation, Lightbulb, Globe, Gavel, Brain,
} from 'lucide-react'
import type { AgentStateEntry, AgentStatus } from '../../types'

const NODES = [
  { id: 'coordinator', icon: Brain, label: 'Coordinator', angle: 0, color: '#818CF8' },
  { id: 'technical', icon: Cpu, label: 'Engineering', angle: 51, color: '#A855F7' },
  { id: 'security', icon: Shield, label: 'Security', angle: 103, color: '#EF4444' },
  { id: 'presentation', icon: Presentation, label: 'Presentation', angle: 154, color: '#A78BFA' },
  { id: 'innovation', icon: Lightbulb, label: 'Innovation', angle: 206, color: '#F59E0B' },
  { id: 'risk', icon: Globe, label: 'Risk', angle: 257, color: '#10B981' },
  { id: 'chief', icon: Gavel, label: 'Chief', angle: 309, color: '#14B8A6' },
]

const EDGES = [
  ['coordinator', 'technical'],
  ['coordinator', 'security'],
  ['coordinator', 'presentation'],
  ['coordinator', 'innovation'],
  ['coordinator', 'risk'],
  ['technical', 'chief'],
  ['security', 'chief'],
  ['presentation', 'chief'],
  ['innovation', 'chief'],
  ['risk', 'chief'],
]

interface AgentNetworkProps {
  activeAgent: string
  agentStates?: Record<string, AgentStateEntry>
  statuses: AgentStatus[]
}

function nodeStatus(
  id: string,
  agentStates?: Record<string, AgentStateEntry>,
  statuses?: AgentStatus[],
  index?: number,
): AgentStatus | 'failed' {
  const state = agentStates?.[id]
  if (state?.status === 'failed') return 'failed'
  if (state?.status === 'completed') return 'completed'
  if (state?.status === 'running') return 'running'
  return statuses?.[index ?? 0] ?? 'waiting'
}

export default function AgentNetwork({ activeAgent, agentStates, statuses }: AgentNetworkProps) {
  const radius = 130
  const cx = 160
  const cy = 160
  const nodePos: Record<string, { x: number; y: number }> = {}

  NODES.forEach(n => {
    const rad = ((n.angle - 90) * Math.PI) / 180
    nodePos[n.id] = { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) }
  })

  const activeEdges = EDGES.filter(([from, to]) => {
    const fromState = agentStates?.[from]?.status
    const toState = agentStates?.[to]?.status
    return fromState === 'running' || fromState === 'completed' || toState === 'running'
  })

  return (
    <div className="relative w-[320px] h-[320px] mx-auto">
      <div className="absolute inset-0 rounded-full border border-violet-500/10 animate-pulse-slow" />
      <div className="absolute inset-6 rounded-full border border-dashed border-purple-500/15" />

      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 320 320">
        {activeEdges.map(([from, to]) => {
          const a = nodePos[from]
          const b = nodePos[to]
          if (!a || !b) return null
          const isFlowing = agentStates?.[from]?.status === 'running' || agentStates?.[to]?.status === 'running'
          return (
            <g key={`${from}-${to}`}>
              <line
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="rgba(6,182,212,0.15)" strokeWidth="1"
              />
              {isFlowing && (
                <motion.circle
                  r="3"
                  fill="#EC4899"
                  initial={{ cx: a.x, cy: a.y }}
                  animate={{ cx: [a.x, b.x], cy: [a.y, b.y] }}
                  transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                  style={{ filter: 'drop-shadow(0 0 4px #EC4899)' }}
                />
              )}
            </g>
          )
        })}
      </svg>

      <motion.div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full bg-gradient-to-br from-violet-500/20 to-pink-500/20 border border-violet-500/40 flex items-center justify-center z-10"
        animate={{
          boxShadow: [
            '0 0 20px rgba(6,182,212,0.25)',
            '0 0 40px rgba(139,92,246,0.35)',
            '0 0 20px rgba(6,182,212,0.25)',
          ],
        }}
        transition={{ duration: 3, repeat: Infinity }}
      >
        <span className="text-[9px] font-mono text-violet-200 font-bold tracking-wider">CORE</span>
      </motion.div>

      {NODES.map((node, i) => {
        const pos = nodePos[node.id]
        const status = nodeStatus(node.id, agentStates, statuses, i)
        const isActive = activeAgent === node.id || activeAgent === 'brief' && node.id === 'coordinator'
        const Icon = node.icon

        return (
          <motion.div
            key={node.id}
            className="absolute z-20 flex flex-col items-center"
            style={{ left: pos.x - 22, top: pos.y - 22 }}
            animate={isActive ? { scale: [1, 1.12, 1] } : { scale: 1 }}
            transition={{ duration: 1.2, repeat: isActive ? Infinity : 0 }}
          >
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center border transition-all duration-300 ${
                status === 'completed'
                  ? 'bg-emerald-500/25 border-emerald-400/50 shadow-[0_0_12px_rgba(16,185,129,0.3)]'
                  : status === 'running'
                    ? 'bg-violet-500/25 border-violet-400/60 shadow-[0_0_16px_rgba(168,85,247,0.4)]'
                    : status === 'failed'
                      ? 'bg-red-500/20 border-red-400/50'
                      : 'bg-white/[0.04] border-white/10'
              }`}
            >
              <Icon
                size={18}
                style={{ color: status === 'waiting' ? '#64748B' : node.color }}
              />
            </div>
            <span className="text-[8px] font-mono text-sentinel-muted mt-1 whitespace-nowrap">
              {node.label}
            </span>
            {agentStates?.[node.id]?.duration_sec != null && status === 'completed' && (
              <span className="text-[7px] font-mono text-emerald-400/70">
                {agentStates[node.id].duration_sec}s
              </span>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}

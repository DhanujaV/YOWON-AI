import { motion } from 'framer-motion'
import {
  Cpu, Shield, Presentation, Lightbulb, Globe, Gavel, Brain,
} from 'lucide-react'
import type { AgentStateEntry, AgentStatus } from '../../types'

const NODES = [
  { id: 'coordinator', icon: Brain, label: 'Coordinator', angle: 0, color: '#00E5FF' },
  { id: 'technical', icon: Cpu, label: 'Forge', angle: 51, color: '#00E5FF' },
  { id: 'security', icon: Shield, label: 'Sentinel', angle: 103, color: '#EF4444' },
  { id: 'presentation', icon: Presentation, label: 'Showcase', angle: 154, color: '#7C3AED' },
  { id: 'innovation', icon: Lightbulb, label: 'Visionary', angle: 206, color: '#00FFA3' },
  { id: 'risk', icon: Globe, label: 'Guardian', angle: 257, color: '#00FFA3' },
  { id: 'chief', icon: Gavel, label: 'Prime', angle: 309, color: '#7C3AED' },
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
  showPresentation?: boolean
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

export default function AgentNetwork({ activeAgent, agentStates, statuses, showPresentation = true }: AgentNetworkProps) {
  const radius = 130
  const cx = 160
  const cy = 160
  const nodePos: Record<string, { x: number; y: number }> = {}
  const nodes = NODES.filter(node => node.id !== 'presentation' || showPresentation).map((node, index, list) => ({
    ...node,
    angle: Math.round(index * 360 / list.length),
  }))
  const edges = EDGES.filter(([from, to]) => (
    showPresentation || (from !== 'presentation' && to !== 'presentation')
  ))

  nodes.forEach(n => {
    const rad = ((n.angle - 90) * Math.PI) / 180
    nodePos[n.id] = { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) }
  })

  const activeEdges = edges.filter(([from, to]) => {
    const fromState = agentStates?.[from]?.status
    const toState = agentStates?.[to]?.status
    return fromState === 'running' || fromState === 'completed' || toState === 'running'
  })

  return (
    <div className="relative w-[320px] h-[320px] mx-auto">
      <div className="absolute inset-0 rounded-full border border-cyan-300/10 animate-pulse-slow" />
      <div className="absolute inset-6 rounded-full border border-dashed border-emerald-300/15" />

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
                stroke="rgba(0,229,255,0.18)" strokeWidth="1"
              />
              {isFlowing && (
                <motion.circle
                  r="3"
                  fill="#00FFA3"
                  initial={{ cx: a.x, cy: a.y }}
                  animate={{ cx: [a.x, b.x], cy: [a.y, b.y] }}
                  transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                  style={{ filter: 'drop-shadow(0 0 5px #00FFA3)' }}
                />
              )}
            </g>
          )
        })}
      </svg>

      <motion.div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-14 h-14 rounded-full bg-gradient-to-br from-cyan-300/20 to-emerald-300/15 border border-cyan-300/40 flex items-center justify-center z-10"
        animate={{
          boxShadow: [
            '0 0 20px rgba(0,229,255,0.25)',
            '0 0 40px rgba(0,255,163,0.26)',
            '0 0 20px rgba(0,229,255,0.25)',
          ],
        }}
        transition={{ duration: 3, repeat: Infinity }}
      >
        <span className="text-[9px] font-mono text-cyan-100 font-bold tracking-wider">CORE</span>
      </motion.div>

      {nodes.map((node, i) => {
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
                    ? 'bg-cyan-300/20 border-cyan-300/60 shadow-[0_0_16px_rgba(0,229,255,0.35)]'
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
            <span className="text-[8px] font-mono text-yowon-muted mt-1 whitespace-nowrap">
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

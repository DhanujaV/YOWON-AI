import { motion } from 'framer-motion'
import {
  Brain, Cpu, Lock, Zap, Globe, Gavel,
} from 'lucide-react'

const NODES = [
  { id: 'coordinator', icon: Brain, label: 'Coordinator', color: '#00E5FF', angle: 270 },
  { id: 'forge',       icon: Cpu,   label: 'Forge',        color: '#22D3EE', angle: 330 },
  { id: 'sentinel',    icon: Lock,  label: 'Sentinel',     color: '#EF4444', angle: 30  },
  { id: 'visionary',   icon: Zap,   label: 'Visionary',    color: '#00FFA3', angle: 90  },
  { id: 'guardian',    icon: Globe, label: 'Guardian',     color: '#00FFA3', angle: 150 },
  { id: 'chief',       icon: Gavel, label: 'Prime',        color: '#7C3AED', angle: 210 },
]

const EDGES = [
  ['coordinator', 'forge'],
  ['coordinator', 'sentinel'],
  ['coordinator', 'visionary'],
  ['coordinator', 'guardian'],
  ['forge',       'chief'],
  ['sentinel',    'chief'],
  ['visionary',   'chief'],
  ['guardian',    'chief'],
]

export default function NeuralNetwork() {
  const CX = 130, CY = 130, R = 90

  const positions: Record<string, { x: number; y: number }> = {}
  NODES.forEach(n => {
    const rad    = ((n.angle - 90) * Math.PI) / 180
    positions[n.id] = { x: CX + R * Math.cos(rad), y: CY + R * Math.sin(rad) }
  })

  return (
    <div className="relative w-[260px] h-[260px] mx-auto">
      {/* Rings */}
      <div className="absolute inset-0 rounded-full border border-cyan-300/10" />
      <div className="absolute inset-8 rounded-full border border-dashed border-emerald-300/10" />

      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 260 260">
        {EDGES.map(([from, to]) => {
          const a = positions[from], b = positions[to]
          if (!a || !b) return null
          return (
            <g key={`${from}-${to}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke="rgba(0,229,255,0.15)" strokeWidth="1" />
              <motion.circle r="2.5" fill="#00FFA3"
                initial={{ cx: a.x, cy: a.y }}
                animate={{ cx: [a.x, b.x], cy: [a.y, b.y] }}
                transition={{ duration: 1.4, repeat: Infinity, ease: 'linear', delay: Math.random() * 1.2 }}
                style={{ filter: 'drop-shadow(0 0 4px #00FFA3)' }}
              />
            </g>
          )
        })}
      </svg>

      {/* Center Core */}
      <motion.div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-gradient-to-br from-cyan-300/20 to-emerald-300/15 border border-cyan-300/40 flex items-center justify-center z-10"
        animate={{ boxShadow: ['0 0 16px rgba(0,229,255,0.25)', '0 0 36px rgba(0,255,163,0.30)', '0 0 16px rgba(0,229,255,0.25)'] }}
        transition={{ duration: 3, repeat: Infinity }}
      >
        <span className="text-[8px] font-mono text-cyan-100 font-bold tracking-wider">CORE</span>
      </motion.div>

      {/* Nodes */}
      {NODES.map(node => {
        const pos  = positions[node.id]
        const Icon = node.icon
        return (
          <motion.div
            key={node.id}
            className="absolute z-20 flex flex-col items-center"
            style={{ left: pos.x - 18, top: pos.y - 18 }}
            animate={{ scale: [1, 1.06, 1] }}
            transition={{ duration: 2.5 + Math.random() * 2, repeat: Infinity, delay: Math.random() * 1.5 }}
          >
            <div className="w-9 h-9 rounded-xl flex items-center justify-center border"
              style={{ background: `${node.color}18`, borderColor: `${node.color}40`, boxShadow: `0 0 10px ${node.color}20` }}>
              <Icon size={15} style={{ color: node.color }} />
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

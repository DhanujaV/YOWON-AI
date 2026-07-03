import { motion } from 'framer-motion'
import {
  Brain, Cpu, Lock, Zap, Star, Globe, Gavel,
} from 'lucide-react'

const AGENTS = [
  {
    icon: Brain,  name: 'Coordinator', role: 'Context Builder',       color: '#00E5FF',
    desc: 'Parses all project inputs and creates the evaluation briefing.',
  },
  {
    icon: Cpu,    name: 'Forge',        role: 'Architecture Agent',    color: '#22D3EE',
    desc: 'Reviews code quality, architecture patterns, and test evidence.',
  },
  {
    icon: Lock,   name: 'Sentinel',     role: 'Security Agent',        color: '#EF4444',
    desc: 'OWASP-style security review and dependency vulnerability scan.',
  },
  {
    icon: Zap,    name: 'Visionary',    role: 'Innovation Agent',      color: '#00FFA3',
    desc: 'Evaluates novelty, ML artifacts, and creative differentiation.',
  },
  {
    icon: Star,   name: 'Showcase',     role: 'Presentation Agent',    color: '#7C3AED',
    desc: 'Scores pitch clarity, documentation, and executive readiness.',
  },
  {
    icon: Globe,  name: 'Guardian',     role: 'Risk Agent',            color: '#00FFA3',
    desc: 'Forecasts failure modes, impact ceiling, and operational risk.',
  },
  {
    icon: Gavel,  name: 'YOWON Prime',  role: 'Chief Judge',           color: '#7C3AED',
    desc: 'Synthesizes all findings into the final binding deployment verdict.',
  },
]

export default function AgentShowcase() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
      {AGENTS.map(({ icon: Icon, name, role, color, desc }, i) => (
        <motion.div
          key={name}
          className="glass-card !p-4 flex flex-col items-center text-center cursor-default group"
          style={{ borderColor: `${color}18` }}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.06 }}
          whileHover={{ y: -3, borderColor: `${color}40` }}
        >
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-all group-hover:scale-110"
            style={{ background: `${color}15`, border: `1px solid ${color}30` }}
          >
            <Icon size={22} style={{ color }} />
          </div>
          <p className="text-xs font-bold text-white mb-0.5" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            {name}
          </p>
          <p className="text-[10px] text-yowon-muted mb-2 uppercase tracking-wider font-mono">
            {role}
          </p>
          <p className="text-[11px] text-yowon-muted leading-relaxed hidden sm:block">
            {desc}
          </p>
          <div className="flex items-center gap-1 mt-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[9px] font-mono text-emerald-400/70 uppercase tracking-wider">Ready</span>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

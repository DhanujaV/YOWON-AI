import { motion } from 'framer-motion'
import {
  Cpu, Shield, Lightbulb, Presentation, AlertTriangle, Gavel,
} from 'lucide-react'

const AGENTS = [
  { icon: Cpu, label: 'Technical Agent', color: '#A855F7', delay: 0 },
  { icon: Shield, label: 'Security Agent', color: '#EF4444', delay: 0.15 },
  { icon: Lightbulb, label: 'Innovation Agent', color: '#F59E0B', delay: 0.3 },
  { icon: Presentation, label: 'Presentation Agent', color: '#EC4899', delay: 0.45 },
  { icon: AlertTriangle, label: 'Risk Agent', color: '#F97316', delay: 0.6 },
  { icon: Gavel, label: 'Verdict Agent', color: '#14B8A6', delay: 0.75 },
]

export default function AgentShowcase() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 max-w-4xl mx-auto">
      {AGENTS.map(({ icon: Icon, label, color, delay }) => (
        <motion.div
          key={label}
          className="glass-card p-4 flex items-center gap-3 group hover:bg-white/[0.04]"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay, duration: 0.5 }}
          whileHover={{ scale: 1.02, borderColor: `${color}40` }}
        >
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 relative"
            style={{ background: `${color}18` }}
          >
            <Icon size={18} style={{ color }} />
            <motion.span
              className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full"
              style={{ background: color, boxShadow: `0 0 8px ${color}` }}
              animate={{ opacity: [1, 0.3, 1], scale: [1, 1.3, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay }}
            />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-display font-medium text-sentinel-text truncate">{label}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-mono text-sentinel-muted uppercase tracking-wider">
                Active
              </span>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

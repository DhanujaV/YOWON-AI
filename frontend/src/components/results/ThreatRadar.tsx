import { motion } from 'framer-motion'
import { Radar } from 'lucide-react'

interface ThreatRadarProps {
  riskLevel: string
  threats?: { label: string; severity: number }[]
}

const DEFAULT_THREATS = [
  { label: 'Security', severity: 0.6 },
  { label: 'Scale', severity: 0.4 },
  { label: 'Compliance', severity: 0.5 },
  { label: 'Ops', severity: 0.35 },
  { label: 'Data', severity: 0.55 },
  { label: 'Vendor', severity: 0.3 },
]

export default function ThreatRadar({
  riskLevel,
  threats = DEFAULT_THREATS,
}: ThreatRadarProps) {
  const riskColors: Record<string, string> = {
    LOW: '#10B981',
    MEDIUM: '#F59E0B',
    HIGH: '#EF4444',
    CRITICAL: '#DC2626',
  }
  const color = riskColors[riskLevel] ?? '#F59E0B'

  return (
    <div className="glass-card p-5 h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Radar size={16} className="text-red-400" />
          <span className="text-xs font-mono text-sentinel-muted uppercase tracking-widest">
            Threat Radar
          </span>
        </div>
        <span
          className="text-xs font-display font-bold px-2 py-0.5 rounded-full"
          style={{ background: `${color}20`, color }}
        >
          {riskLevel} RISK
        </span>
      </div>

      <div className="relative w-full aspect-square max-w-[200px] mx-auto">
        {/* Radar rings */}
        {[1, 0.66, 0.33].map((scale, i) => (
          <div
            key={i}
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/10"
            style={{ width: `${scale * 100}%`, height: `${scale * 100}%` }}
          />
        ))}

        {/* Sweep line */}
        <motion.div
          className="absolute left-1/2 top-1/2 origin-bottom w-px h-1/2 -ml-px"
          style={{
            background: 'linear-gradient(to top, transparent, rgba(6,182,212,0.8))',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        />

        {/* Threat blips */}
        {threats.map((t, i) => {
          const angle = (i / threats.length) * Math.PI * 2 - Math.PI / 2
          const r = t.severity * 42
          const x = 50 + (r * Math.cos(angle)) / 2
          const y = 50 + (r * Math.sin(angle)) / 2
          return (
            <motion.div
              key={t.label}
              className="absolute w-2 h-2 rounded-full"
              style={{
                left: `${x}%`,
                top: `${y}%`,
                background: color,
                boxShadow: `0 0 8px ${color}`,
              }}
              animate={{ opacity: [0.5, 1, 0.5], scale: [1, 1.4, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
            />
          )
        })}

        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-violet-400" />
      </div>
    </div>
  )
}

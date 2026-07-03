import { motion } from 'framer-motion'
import { Radar, ShieldAlert } from 'lucide-react'

interface ThreatRadarProps {
  riskLevel: string
  threats?: { label: string; severity: number }[]
}

const DEFAULT_THREATS = [
  { label: 'Security',   severity: 0.65 },
  { label: 'Ops Fail',   severity: 0.45 },
  { label: 'Compliance', severity: 0.55 },
  { label: 'Auth Post',  severity: 0.38 },
  { label: 'Leaks',      severity: 0.58 },
  { label: 'Dependencies', severity: 0.32 },
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
    <div className="cyber-glow-card h-full">
      <div className="cyber-glow-inner !p-5 flex flex-col justify-between h-full">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Radar size={15} className="text-red-400 animate-pulse" />
            <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em]">
              Sentinel Threat Radar
            </span>
          </div>
          <span
            className="text-[9px] font-mono font-bold px-2 py-0.5 rounded-full border"
            style={{
              background: `${color}12`,
              borderColor: `${color}40`,
              color,
              boxShadow: `0 0 10px ${color}18`,
            }}
          >
            {riskLevel} RISK
          </span>
        </div>

        <div className="relative w-full aspect-square max-w-[210px] mx-auto">
          {/* Radar rings */}
          {[1, 0.75, 0.5, 0.25].map((scale, i) => (
            <div
              key={i}
              className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.06]"
              style={{
                width: `${scale * 100}%`,
                height: `${scale * 100}%`,
                borderStyle: i % 2 === 0 ? 'solid' : 'dashed',
              }}
            />
          ))}

          {/* Crosshairs */}
          <div className="absolute inset-y-0 left-1/2 w-px bg-white/[0.04]" />
          <div className="absolute inset-x-0 top-1/2 h-px bg-white/[0.04]" />

          {/* Spinning sweep line */}
          <motion.div
            className="absolute left-1/2 top-1/2 origin-bottom w-px h-1/2 -ml-px"
            style={{
              background: 'linear-gradient(to top, transparent, rgba(0, 229, 255, 0.6))',
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: 4.8, repeat: Infinity, ease: 'linear' }}
          />

          {/* Threat blips and spokes */}
          {threats.map((t, i) => {
            const angle = (i / threats.length) * Math.PI * 2 - Math.PI / 2
            const r     = t.severity * 45 // radius offset
            const x     = 50 + (r * Math.cos(angle))
            const y     = 50 + (r * Math.sin(angle))
            
            return (
              <div key={t.label}>
                {/* Dashed spoke line from center to dot */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
                  <line
                    x1="50" y1="50" x2={x} y2={y}
                    stroke={`${color}22`}
                    strokeWidth="0.5"
                    strokeDasharray="2,2"
                  />
                </svg>

                {/* Pulsing Threat blip */}
                <motion.div
                  className="absolute w-2 h-2 rounded-full z-10"
                  style={{
                    left: `calc(${x}% - 4px)`,
                    top: `calc(${y}% - 4px)`,
                    background: color,
                    boxShadow: `0 0 12px ${color}`,
                  }}
                  animate={{ scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
                  transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
                />

                {/* Threat labels */}
                <span
                  className="absolute text-[8px] font-mono text-yowon-muted whitespace-nowrap bg-[#09090b]/80 px-1 rounded select-none border border-white/[0.03]"
                  style={{
                    left: `${x}%`,
                    top: `${y}%`,
                    transform: `translate(${Math.cos(angle) * 8}px, ${Math.sin(angle) * 8 - 4}px)`,
                  }}
                >
                  {t.label}
                </span>
              </div>
            )
          })}

          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-violet-400 border border-white/20" />
        </div>

        <div className="mt-3 text-center flex items-center justify-center gap-1.5 text-[9px] font-mono text-yowon-muted">
          <ShieldAlert size={11} className="text-red-400" />
          <span>Real-time Sentinel Audit Analysis</span>
        </div>
      </div>
    </div>
  )
}

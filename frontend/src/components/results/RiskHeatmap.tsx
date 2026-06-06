import { motion } from 'framer-motion'
import { scoreColor } from '../../utils/reportParser'

interface RiskHeatmapProps {
  categories: { label: string; score: number }[]
}

export default function RiskHeatmap({ categories }: RiskHeatmapProps) {
  return (
    <div className="glass-card p-5">
      <h3 className="text-xs font-mono text-sentinel-muted uppercase tracking-widest mb-4">
        Risk Heatmap
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {categories.map((cat, i) => {
          const risk = 100 - cat.score
          const intensity = risk / 100
          const color = scoreColor(cat.score)

          return (
            <motion.div
              key={cat.label}
              className="rounded-lg p-3 border border-white/5 relative overflow-hidden"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.08 }}
              style={{
                background: `linear-gradient(135deg, ${color}${Math.round(intensity * 30).toString(16).padStart(2, '0')}, transparent)`,
              }}
            >
              <p className="text-xs font-display text-sentinel-text">{cat.label}</p>
              <p className="text-lg font-bold font-mono mt-1" style={{ color }}>
                {Math.round(cat.score)}
              </p>
              <p className="text-[10px] text-sentinel-muted font-mono">
                Risk: {Math.round(risk)}%
              </p>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

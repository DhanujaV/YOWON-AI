import type { ElementType } from 'react'
import { motion } from 'framer-motion'
import {
  FileText, ThumbsUp, ThumbsDown, AlertOctagon, Wrench, Map,
} from 'lucide-react'
import type { VerdictData } from '../../types'

interface ExecutiveSummaryProps {
  data: VerdictData
}

function SectionCard({
  icon: Icon,
  title,
  items,
  color,
  delay,
}: {
  icon: ElementType
  title: string
  items: string[]
  color: string
  delay: number
}) {
  if (!items.length) return null

  return (
    <motion.div
      className="glass-card p-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} style={{ color }} />
        <h3 className="font-display font-semibold text-sentinel-text">{title}</h3>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-sm text-sentinel-muted leading-relaxed">
            <span className="text-sentinel-accent mt-1.5 flex-shrink-0">▸</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  )
}

export default function ExecutiveSummary({ data }: ExecutiveSummaryProps) {
  return (
    <div className="space-y-6">
      {data.executive_summary && (
        <motion.div
          className="glass-card p-6 border-l-2 border-sentinel-accent"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="flex items-center gap-2 mb-3">
            <FileText size={18} className="text-sentinel-accent" />
            <h2 className="font-display font-bold text-xl text-sentinel-text">
              Executive Summary
            </h2>
          </div>
          <p className="text-sentinel-muted leading-relaxed">{data.executive_summary}</p>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard
          icon={ThumbsUp}
          title="Top Strengths"
          items={data.top_strengths ?? []}
          color="#10B981"
          delay={0.1}
        />
        <SectionCard
          icon={ThumbsDown}
          title="Top Weaknesses"
          items={data.top_weaknesses ?? []}
          color="#F59E0B"
          delay={0.2}
        />
        <SectionCard
          icon={AlertOctagon}
          title="Blocking Issues"
          items={data.blocking_issues ?? []}
          color="#EF4444"
          delay={0.3}
        />
        <SectionCard
          icon={Wrench}
          title="Recommended Fixes"
          items={data.recommended_fixes ?? []}
          color="#A855F7"
          delay={0.4}
        />
      </div>

      {(data.deployment_roadmap?.length ?? 0) > 0 && (
        <SectionCard
          icon={Map}
          title="Deployment Roadmap"
          items={data.deployment_roadmap ?? []}
          color="#EC4899"
          delay={0.5}
        />
      )}
    </div>
  )
}

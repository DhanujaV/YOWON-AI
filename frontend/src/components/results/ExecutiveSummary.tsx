import type { ElementType } from 'react'
import { motion } from 'framer-motion'
import {
  FileText, ThumbsUp, ThumbsDown, AlertOctagon, Wrench, Map, CheckCircle2,
} from 'lucide-react'
import type { VerdictData } from '../../types'
import { normalizeDisplayList, phaseDeploymentRoadmap } from '../../utils/listNormalizer'

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
        <h3 className="font-display font-semibold text-yowon-text">{title}</h3>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-sm text-yowon-muted leading-relaxed">
            <span className="text-yowon-accent mt-1.5 flex-shrink-0">-</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </motion.div>
  )
}

function DeploymentRoadmap({
  items,
}: {
  items: string[] | string | undefined
}) {
  const phases = phaseDeploymentRoadmap(items)

  return (
    <motion.div
      className="glass-card p-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Map size={16} style={{ color: '#EC4899' }} />
        <h3 className="font-display font-semibold text-yowon-text">Deployment Roadmap</h3>
      </div>
      {phases.length === 0 ? (
        <p className="text-sm text-yowon-muted">No deployment roadmap generated.</p>
      ) : (
        <div className="space-y-4">
          {phases.map(phase => (
            <div key={phase.title}>
              <p className="text-sm font-display font-semibold text-yowon-text mb-2">{phase.title}</p>
              <ul className="space-y-2">
                {phase.items.map((item, i) => (
                  <li key={`${phase.title}-${i}`} className="flex gap-2 text-sm text-yowon-muted leading-relaxed">
                    <span className="text-yowon-accent mt-1.5 flex-shrink-0">-</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}

export default function ExecutiveSummary({ data }: ExecutiveSummaryProps) {
  const strengths = normalizeDisplayList(data.top_strengths)
  const weaknesses = normalizeDisplayList(data.top_weaknesses)
  const blocking = normalizeDisplayList(data.blocking_issues)
  const fixes = normalizeDisplayList(data.recommended_fixes)
  const confidenceSources = normalizeDisplayList(data.confidence_sources)
  const roadmap = data.roadmap ?? data.deployment_roadmap

  return (
    <div className="space-y-6">
      {data.executive_summary && (
        <motion.div
          className="glass-card p-6 border-l-2 border-yowon-accent"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="flex items-center gap-2 mb-3">
            <FileText size={18} className="text-yowon-accent" />
            <h2 className="font-display font-bold text-xl text-yowon-text">
              Executive Summary
            </h2>
          </div>
          <p className="text-yowon-muted leading-relaxed">{data.executive_summary}</p>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SectionCard
          icon={ThumbsUp}
          title="Top Strengths"
          items={strengths}
          color="#10B981"
          delay={0.1}
        />
        <SectionCard
          icon={ThumbsDown}
          title="Top Weaknesses"
          items={weaknesses}
          color="#F59E0B"
          delay={0.2}
        />
        <SectionCard
          icon={AlertOctagon}
          title="Blocking Issues"
          items={blocking}
          color="#EF4444"
          delay={0.3}
        />
        <SectionCard
          icon={Wrench}
          title="Recommended Fixes"
          items={fixes}
          color="#A855F7"
          delay={0.4}
        />
        <SectionCard
          icon={CheckCircle2}
          title="Confidence Sources"
          items={confidenceSources}
          color="#14B8A6"
          delay={0.45}
        />
      </div>

      <DeploymentRoadmap items={roadmap} />
    </div>
  )
}

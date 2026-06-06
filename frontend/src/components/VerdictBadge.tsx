import { motion } from 'framer-motion'
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react'

interface VerdictBadgeProps {
  verdict: 'ACCEPT' | 'IMPROVE' | 'REJECT' | string
  large?: boolean
  animated?: boolean
}

const VERDICT_CONFIG = {
  ACCEPT: {
    icon: CheckCircle,
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-400',
    glow: 'shadow-[0_0_40px_rgba(16,185,129,0.25)]',
  },
  IMPROVE: {
    icon: AlertTriangle,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    glow: 'shadow-[0_0_40px_rgba(245,158,11,0.25)]',
  },
  REJECT: {
    icon: XCircle,
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    glow: 'shadow-[0_0_40px_rgba(239,68,68,0.25)]',
  },
}

export default function VerdictBadge({ verdict, large = false, animated = false }: VerdictBadgeProps) {
  const config = VERDICT_CONFIG[verdict as keyof typeof VERDICT_CONFIG] || VERDICT_CONFIG.IMPROVE
  const Icon = config.icon
  const Wrapper = animated ? motion.div : 'div'
  const animProps = animated
    ? {
        initial: { scale: 0.5, opacity: 0 },
        animate: { scale: 1, opacity: 1 },
        transition: { type: 'spring' as const, stiffness: 260, damping: 18 },
      }
    : {}

  if (large) {
    return (
      <Wrapper
        className={`inline-flex items-center gap-4 px-8 py-4 rounded-2xl border ${config.bg} ${config.border} ${config.glow}`}
        {...animProps}
      >
        <Icon className={config.text} size={36} />
        <span className={`text-4xl font-bold font-display tracking-tight ${config.text}`}>
          {verdict}
        </span>
      </Wrapper>
    )
  }

  return (
    <Wrapper
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${config.bg} ${config.border}`}
      {...animProps}
    >
      <Icon className={config.text} size={14} />
      <span className={`text-sm font-semibold font-display ${config.text}`}>{verdict}</span>
    </Wrapper>
  )
}

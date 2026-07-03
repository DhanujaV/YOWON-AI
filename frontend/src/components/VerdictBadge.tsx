import { motion } from 'framer-motion'
import { CheckCircle, AlertTriangle, XCircle, ShieldCheck } from 'lucide-react'

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
    glowColor: 'rgba(16,185,129,0.3)',
    status: 'SYSTEM_VERDICT::VERIFIED_ACCEPT',
  },
  IMPROVE: {
    icon: AlertTriangle,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    glowColor: 'rgba(245,158,11,0.3)',
    status: 'SYSTEM_VERDICT::REVISIONS_REQUIRED',
  },
  REJECT: {
    icon: XCircle,
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    glowColor: 'rgba(239,68,68,0.3)',
    status: 'SYSTEM_VERDICT::DEPLOYMENT_REJECTED',
  },
}

export default function VerdictBadge({ verdict, large = false, animated = false }: VerdictBadgeProps) {
  const config = VERDICT_CONFIG[verdict as keyof typeof VERDICT_CONFIG] || VERDICT_CONFIG.IMPROVE
  const Icon = config.icon
  const Wrapper = animated ? motion.div : 'div'
  const animProps = animated
    ? {
        initial: { scale: 0.8, opacity: 0 },
        animate: { scale: 1, opacity: 1 },
        transition: { type: 'spring' as const, stiffness: 200, damping: 18 },
      }
    : {}

  if (large) {
    return (
      <Wrapper
        className="relative p-0.5 rounded-2xl overflow-hidden"
        style={{
          boxShadow: `0 0 50px ${config.glowColor}, inset 0 0 15px rgba(255,255,255,0.05)`,
        }}
        {...animProps}
      >
        {/* Background neon border trail */}
        <div
          className="absolute inset-0 -z-10 animate-[spin_5s_linear_infinite]"
          style={{
            background: `conic-gradient(from 0deg, transparent 40%, ${config.glowColor} 60%, transparent 80%)`,
          }}
        />

        <div className={`flex flex-col sm:flex-row items-center gap-4 px-10 py-6 rounded-[15px] bg-[#0c0d12] border border-white/5`}>
          <div className="flex items-center gap-4">
            <div
              className="p-3.5 rounded-xl border flex items-center justify-center"
              style={{
                borderColor: `${config.glowColor}`,
                background: `${config.glowColor.replace('0.3', '0.08')}`,
              }}
            >
              <Icon className={config.text} size={32} />
            </div>
            <div className="text-left">
              <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.25em] block mb-1">
                {config.status}
              </span>
              <span className={`text-4xl font-extrabold font-display tracking-tight ${config.text}`}>
                {verdict}
              </span>
            </div>
          </div>
          
          <div className="h-px w-full sm:h-12 sm:w-px bg-white/10 shrink-0" />
          
          <div className="flex items-center gap-2 text-left">
            <ShieldCheck size={16} className="text-cyan-400 shrink-0" />
            <div>
              <p className="text-[9px] font-mono text-cyan-300 uppercase tracking-widest leading-none">Jury Verdict</p>
              <p className="text-[10px] text-yowon-muted mt-1 leading-normal font-semibold">100% Deterministic Rubric</p>
            </div>
          </div>
        </div>
      </Wrapper>
    )
  }

  return (
    <Wrapper
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border ${config.bg} ${config.border}`}
      {...animProps}
    >
      <Icon className={config.text} size={14} />
      <span className={`text-xs font-semibold font-display ${config.text}`}>{verdict}</span>
    </Wrapper>
  )
}

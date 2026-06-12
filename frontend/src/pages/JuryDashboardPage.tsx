import { motion } from 'framer-motion'
import { Brain, Code2, Presentation, Scale, ShieldCheck } from 'lucide-react'
import AppShell from '../components/layout/AppShell'

const JUDGES = [
  {
    name: 'Forge',
    icon: Code2,
    color: '#38BDF8',
    finding: 'Reviews architecture, implementation quality, modularity, tests, and code evidence.',
  },
  {
    name: 'Sentinel',
    icon: ShieldCheck,
    color: '#7C3AED',
    finding: 'Assesses exposed secrets, dependency risk, authentication posture, and reliability hazards.',
  },
  {
    name: 'Visionary',
    icon: Brain,
    color: '#22D3EE',
    finding: 'Scores novelty, trained model artifacts, dataset evidence, differentiation, and creative execution.',
  },
  {
    name: 'Showcase',
    icon: Presentation,
    color: '#00FFA3',
    finding: 'Evaluates pitch clarity, documentation quality, roadmap quality, and executive readiness.',
  },
  {
    name: 'Guardian',
    icon: Scale,
    color: '#00FFA3',
    finding: 'Forecasts impact, operational risk, failure modes, and confidence limits from available evidence.',
  },
]

export default function JuryDashboardPage() {
  return (
    <AppShell particles>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14 space-y-8">
        <section className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 glass-pill px-3 py-1.5 mb-4 border-cyan-300/20">
            <Brain size={13} className="text-cyan-300" />
            <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-widest">AI Jury Dashboard</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-display font-bold text-yowon-text">
            Council
          </h1>
          <p className="text-yowon-muted mt-3">
            A transparent view of the autonomous jury roles that synthesize project intelligence.
          </p>
        </section>

        <section className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {JUDGES.map((judge, index) => {
            const Icon = judge.icon
            return (
              <motion.div
                key={judge.name}
                className="glass-card p-6 border-white/10"
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.06 }}
              >
                <div className="flex items-center gap-3 mb-5">
                  <div
                    className="w-11 h-11 rounded-lg flex items-center justify-center"
                    style={{ background: `${judge.color}22` }}
                  >
                    <Icon size={20} style={{ color: judge.color }} />
                  </div>
                  <div>
                    <h2 className="font-display font-semibold text-yowon-text">{judge.name}</h2>
                    <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">READY</p>
                  </div>
                </div>
                <p className="text-sm leading-relaxed text-yowon-muted">{judge.finding}</p>
              </motion.div>
            )
          })}
        </section>
      </main>
    </AppShell>
  )
}

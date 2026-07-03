import { motion } from 'framer-motion'
import {
  Brain, Code2, Presentation, Scale, ShieldCheck, Gavel,
  Cpu, Lock, Star, Globe, Zap, Radio,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'

const JUDGES = [
  {
    name: 'Coordinator',
    icon: Brain,
    color: '#00E5FF',
    role: 'Context Builder',
    finding: 'Orchestrates the evaluation council, parses all project inputs, and builds the context briefing that every other agent uses.',
  },
  {
    name: 'Forge',
    icon: Cpu,
    color: '#22D3EE',
    role: 'Architecture Agent',
    finding: 'Reviews code architecture, implementation quality, modularity, test coverage, and engineering evidence depth.',
  },
  {
    name: 'Sentinel',
    icon: Lock,
    color: '#EF4444',
    role: 'Security Agent',
    finding: 'Assesses exposed secrets, dependency vulnerability chains, authentication posture, and reliability hazard maps.',
  },
  {
    name: 'Visionary',
    icon: Zap,
    color: '#00FFA3',
    role: 'Innovation Agent',
    finding: 'Scores novelty, trained model artifacts, dataset evidence, differentiation signals, and creative technical execution.',
  },
  {
    name: 'Showcase',
    icon: Star,
    color: '#7C3AED',
    role: 'Presentation Agent',
    finding: 'Evaluates pitch clarity, slide quality, documentation completeness, roadmap quality, and executive communication.',
  },
  {
    name: 'Guardian',
    icon: Globe,
    color: '#00FFA3',
    role: 'Risk Agent',
    finding: 'Forecasts deployment impact, operational failure modes, confidence limits, and scalability ceilings from available evidence.',
  },
  {
    name: 'YOWON Prime',
    icon: Gavel,
    color: '#7C3AED',
    role: 'Chief Judge',
    finding: 'Cross-examines all Council findings, resolves contradictions, and renders the final binding deployment verdict.',
  },
]

export default function JuryDashboardPage() {
  return (
    <AppShell particles>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14 space-y-10">

        {/* Header */}
        <section className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 glass-pill px-3.5 py-1.5 mb-5 border-cyan-300/15">
            <Brain size={13} className="text-cyan-300" />
            <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em]">
              AI Jury Dashboard
            </span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-white mb-4"
            style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            The <span className="gradient-text">Council</span>
          </h1>
          <p className="text-yowon-muted text-sm max-w-lg mx-auto leading-relaxed">
            A transparent view of the seven autonomous AI agents that together synthesize
            judge-grade project intelligence. Each operates independently, then YOWON Prime
            reconciles all findings into a single binding verdict.
          </p>
        </section>

        {/* Live indicator */}
        <div className="flex items-center justify-center gap-3">
          <div className="flex items-center gap-2 glass-pill px-4 py-2">
            <Radio size={11} className="text-emerald-400 animate-pulse" />
            <span className="text-[11px] font-mono text-yowon-muted uppercase tracking-[0.2em]">
              7 Agents · Ready
            </span>
          </div>
        </div>

        {/* Agent grid */}
        <section className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {JUDGES.map((judge, index) => {
            const Icon     = judge.icon
            const isChief  = judge.name === 'YOWON Prime'
            return (
              <motion.div
                key={judge.name}
                className={`glass-card !p-0 overflow-hidden ${isChief ? 'md:col-span-2 xl:col-span-3' : ''}`}
                style={{ borderColor: `${judge.color}22` }}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.07 }}
                whileHover={{ y: -2 }}
              >
                {/* Colored top bar */}
                <div className="h-0.5 w-full" style={{ background: `linear-gradient(90deg, ${judge.color}, transparent)` }} />

                <div className={`p-5 ${isChief ? 'sm:flex sm:items-center sm:gap-6' : ''}`}>
                  <div className={`flex items-center gap-3 mb-4 ${isChief ? 'sm:mb-0 sm:shrink-0' : ''}`}>
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center border"
                      style={{ background: `${judge.color}18`, borderColor: `${judge.color}35` }}
                    >
                      <Icon size={22} style={{ color: judge.color }} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="font-bold text-white" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                          {judge.name}
                        </h2>
                        {isChief && (
                          <span className="status-badge info text-[9px]">Chief Judge</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-yowon-muted">
                          {judge.role}
                        </p>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm leading-relaxed text-yowon-muted">{judge.finding}</p>
                </div>
              </motion.div>
            )
          })}
        </section>

        {/* Footnote */}
        <p className="text-center text-[11px] text-yowon-muted/60 font-mono">
          All agents run in parallel · Powered by local Ollama models · No data leaves your system
        </p>
      </main>
    </AppShell>
  )
}

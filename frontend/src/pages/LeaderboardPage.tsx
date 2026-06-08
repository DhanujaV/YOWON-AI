import { motion } from 'framer-motion'
import { Award, Crown, Medal, ShieldCheck, TrendingUp } from 'lucide-react'
import AppShell from '../components/layout/AppShell'

const PROJECTS = [
  { rank: 1, project: 'NeuroDeploy', team: 'Vector Labs', score: 94, confidence: 92 },
  { rank: 2, project: 'MediAssist', team: 'CareForge', score: 89, confidence: 86 },
  { rank: 3, project: 'GridWatch', team: 'SignalWorks', score: 84, confidence: 81 },
  { rank: 4, project: 'EduPilot', team: 'Northstar', score: 78, confidence: 74 },
  { rank: 5, project: 'FinSight', team: 'Ledger AI', score: 73, confidence: 71 },
]

function PodiumCard({ item, delay }: { item: (typeof PROJECTS)[number]; delay: number }) {
  const Icon = item.rank === 1 ? Crown : item.rank === 2 ? Award : Medal
  return (
    <motion.div
      className="glass-card p-5 border-white/10"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
    >
      <div className="flex items-center justify-between mb-5">
        <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
          <Icon size={20} className={item.rank === 1 ? 'text-amber-300' : item.rank === 2 ? 'text-violet-300' : 'text-cyan-300'} />
        </div>
        <span className="text-xs font-mono text-yowon-muted">RANK {item.rank}</span>
      </div>
      <h2 className="text-xl font-display font-bold text-yowon-text">{item.project}</h2>
      <p className="text-sm text-yowon-muted mt-1">{item.team}</p>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-white/5 p-3">
          <p className="text-[10px] font-mono uppercase text-yowon-muted">Score</p>
          <p className="text-2xl font-display font-bold text-emerald-300">{item.score}</p>
        </div>
        <div className="rounded-lg border border-white/5 p-3">
          <p className="text-[10px] font-mono uppercase text-yowon-muted">Confidence</p>
          <p className="text-2xl font-display font-bold text-cyan-300">{item.confidence}</p>
        </div>
      </div>
    </motion.div>
  )
}

export default function LeaderboardPage() {
  return (
    <AppShell particles>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14 space-y-8">
        <section className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 glass-pill px-3 py-1.5 mb-4 border-cyan-500/20">
              <TrendingUp size={13} className="text-cyan-300" />
              <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-widest">Future Leaderboard</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-display font-bold text-yowon-text">
              AI Jury Rankings
            </h1>
            <p className="text-yowon-muted mt-3 max-w-2xl">
              Score, confidence, and project intelligence summaries for evaluated teams.
            </p>
          </div>
          <div className="glass-card p-4 min-w-56">
            <p className="text-xs font-mono text-yowon-muted uppercase">Evaluation Pool</p>
            <p className="text-3xl font-display font-bold text-yowon-text mt-1">{PROJECTS.length}</p>
          </div>
        </section>

        <section className="grid md:grid-cols-3 gap-4">
          {PROJECTS.slice(0, 3).map((item, i) => (
            <PodiumCard key={item.project} item={item} delay={i * 0.08} />
          ))}
        </section>

        <section className="glass-card overflow-x-auto">
          <div className="min-w-[720px]">
            <div className="grid grid-cols-[64px_1.2fr_1fr_96px_120px] gap-3 px-4 py-3 text-[10px] font-mono uppercase tracking-widest text-yowon-muted border-b border-white/5">
              <span>Rank</span>
              <span>Project</span>
              <span>Team</span>
              <span>Score</span>
              <span>Confidence</span>
            </div>
            {PROJECTS.map(item => (
              <div
                key={item.project}
                className="grid grid-cols-[64px_1.2fr_1fr_96px_120px] gap-3 px-4 py-4 text-sm border-b border-white/5 last:border-b-0"
              >
                <span className="font-mono text-yowon-muted">#{item.rank}</span>
                <span className="font-display font-semibold text-yowon-text">{item.project}</span>
                <span className="text-yowon-muted">{item.team}</span>
                <span className="text-emerald-300 font-mono">{item.score}/100</span>
                <span className="text-cyan-300 font-mono">{item.confidence}/100</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </AppShell>
  )
}

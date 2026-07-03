import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Trophy, Star, Clock, TrendingUp, BarChart3, Sparkles } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { api } from '../api/api'
import { scoreColor } from '../utils/reportParser'

interface ProjectSummary {
  project_id: string
  project_name?: string
  project_type?: string
  status?: string
  overall_score?: number | null
  created_at?: string
}

export default function LeaderboardPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading,  setLoading]  = useState(true)
  const [filter,   setFilter]   = useState('')

  useEffect(() => {
    api.get<ProjectSummary[]>('/projects')
      .then(({ data }) => {
        const sorted = [...data]
          .filter(p => p.status === 'completed' && p.overall_score != null)
          .sort((a, b) => (b.overall_score ?? 0) - (a.overall_score ?? 0))
        setProjects(sorted)
      })
      .finally(() => setLoading(false))
  }, [])

  const filtered = projects.filter(
    p => !filter || p.project_name?.toLowerCase().includes(filter.toLowerCase())
  )

  const podium  = filtered.slice(0, 3)
  const rest    = filtered.slice(3)

  const podiumColors = [
    { ring: '#F59E0B', label: 'text-amber-400',  icon: '🥇', glow: 'rgba(245,158,11,0.30)' },
    { ring: '#94A3B8', label: 'text-slate-400',  icon: '🥈', glow: 'rgba(148,163,184,0.20)' },
    { ring: '#B45309', label: 'text-amber-600',  icon: '🥉', glow: 'rgba(180,83,9,0.22)'   },
  ]

  return (
    <AppShell>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-14">

        {/* Header */}
        <motion.div
          className="text-center mb-10"
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        >
          <div className="inline-flex items-center gap-2 glass-pill px-3.5 py-1.5 mb-5 border-amber-300/15">
            <Trophy size={12} className="text-amber-400" />
            <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em]">
              Global Rankings
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mb-3 text-white"
            style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            AI Jury <span className="gradient-text">Leaderboard</span>
          </h1>
          <p className="text-yowon-muted text-sm max-w-sm mx-auto">
            Ranked by overall YOWON AI readiness score across all submissions.
          </p>
        </motion.div>

        {/* Podium — top 3 */}
        {podium.length >= 2 && !loading && (
          <motion.div
            className="grid grid-cols-3 gap-4 mb-10 items-end"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            {/* 2nd */}
            {podium[1] && (
              <div className="glass-card !p-5 text-center"
                style={{ borderColor: podiumColors[1].ring + '40', boxShadow: `0 0 32px ${podiumColors[1].glow}` }}>
                <p className="text-3xl mb-2">🥈</p>
                <p className="font-semibold text-sm text-white truncate">{podium[1].project_name}</p>
                <p className="text-3xl font-black mt-2 font-mono"
                  style={{ color: scoreColor(podium[1].overall_score ?? 0) }}>
                  {podium[1].overall_score}
                </p>
                <p className="text-[10px] text-yowon-muted mt-1 font-mono uppercase tracking-widest">#2</p>
              </div>
            )}
            {/* 1st — slightly larger */}
            {podium[0] && (
              <div className="glass-card !p-6 text-center -mt-4"
                style={{ borderColor: podiumColors[0].ring + '60', boxShadow: `0 0 48px ${podiumColors[0].glow}` }}>
                <p className="text-4xl mb-2">🥇</p>
                <div className="w-8 h-8 bg-amber-400/20 border border-amber-400/40 rounded-full flex items-center justify-center mx-auto mb-2">
                  <Star size={14} className="text-amber-400" />
                </div>
                <p className="font-bold text-base text-white truncate">{podium[0].project_name}</p>
                <p className="text-4xl font-black mt-2 font-mono"
                  style={{ color: scoreColor(podium[0].overall_score ?? 0) }}>
                  {podium[0].overall_score}
                </p>
                <p className="text-[10px] text-amber-400/80 mt-1 font-mono uppercase tracking-widest">#1 · Champion</p>
              </div>
            )}
            {/* 3rd */}
            {podium[2] && (
              <div className="glass-card !p-5 text-center"
                style={{ borderColor: podiumColors[2].ring + '40', boxShadow: `0 0 24px ${podiumColors[2].glow}` }}>
                <p className="text-3xl mb-2">🥉</p>
                <p className="font-semibold text-sm text-white truncate">{podium[2].project_name}</p>
                <p className="text-3xl font-black mt-2 font-mono"
                  style={{ color: scoreColor(podium[2].overall_score ?? 0) }}>
                  {podium[2].overall_score}
                </p>
                <p className="text-[10px] text-yowon-muted mt-1 font-mono uppercase tracking-widest">#3</p>
              </div>
            )}
          </motion.div>
        )}

        {/* Summary stats */}
        {!loading && filtered.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: 'Total Submissions', value: filtered.length, icon: BarChart3, color: 'text-cyan-300' },
              { label: 'Avg Score', value: `${Math.round(filtered.reduce((s, p) => s + (p.overall_score ?? 0), 0) / filtered.length)}/100`, icon: TrendingUp, color: 'text-emerald-400' },
              { label: 'Top Score', value: `${filtered[0]?.overall_score ?? 0}/100`, icon: Sparkles, color: 'text-amber-400' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="metric-card text-center">
                <Icon size={15} className={`mx-auto mb-1 ${color}`} />
                <p className="mc-value text-xl">{value}</p>
                <p className="mc-label">{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filter */}
        <div className="mb-4">
          <input
            className="yowon-input max-w-xs text-sm"
            placeholder="Search by project name..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
          />
        </div>

        {/* Table — rest of rankings */}
        {loading ? (
          <div className="text-center py-24 text-yowon-muted">
            <div className="w-10 h-10 border-2 border-violet-400/30 border-t-violet-400 rounded-full mx-auto mb-3 animate-spin" />
            <p className="font-mono text-sm">Loading rankings...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass-card text-center !py-16">
            <Trophy size={36} className="mx-auto mb-3 text-yowon-muted opacity-30" />
            <p className="text-yowon-muted font-semibold">No completed evaluations yet.</p>
            <p className="text-yowon-muted text-sm mt-1">Submit a project to appear here!</p>
          </div>
        ) : (
          <div className="glass-card !p-0 overflow-hidden">
            {rest.map((project, i) => {
              const rank  = i + 4
              const score = project.overall_score ?? 0
              const color = scoreColor(score)
              return (
                <motion.div
                  key={project.project_id}
                  className="flex items-center gap-4 px-5 py-4 border-b border-white/[0.06] hover:bg-white/[0.025] transition-all last:border-0"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <span className="w-10 text-center font-mono text-xs font-bold text-yowon-muted">#{rank}</span>

                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm text-white truncate">{project.project_name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {project.project_type && (
                        <span className="tech-chip text-[10px] !py-0.5">{project.project_type}</span>
                      )}
                      <span className="text-[10px] text-yowon-muted font-mono flex items-center gap-1">
                        <Clock size={9} />
                        {new Date(project.created_at ?? '').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                  </div>

                  <div className="w-24 hidden sm:block">
                    <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: color }}
                        initial={{ width: 0 }}
                        animate={{ width: `${score}%` }}
                        transition={{ duration: 0.6, delay: i * 0.03 }}
                      />
                    </div>
                  </div>

                  <span className="font-black font-mono text-lg w-14 text-right shrink-0"
                    style={{ color }}>
                    {score}
                  </span>
                </motion.div>
              )
            })}
          </div>
        )}
      </main>
    </AppShell>
  )
}

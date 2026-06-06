import { useEffect, useState, type ElementType } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { motion } from 'framer-motion'
import {
  Download, ArrowLeft, Shield, ChevronDown, ChevronUp,
  Cpu, Lock, Star, Zap, Globe, AlertTriangle, TrendingUp, Activity,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import ScoreRing from '../components/ScoreRing'
import VerdictReveal from '../components/results/VerdictReveal'
import ConfidenceMeter from '../components/results/ConfidenceMeter'
import ThreatRadar from '../components/results/ThreatRadar'
import ReadinessGauge from '../components/results/ReadinessGauge'
import AgentConsensus from '../components/results/AgentConsensus'
import RiskHeatmap from '../components/results/RiskHeatmap'
import ExecutiveSummary from '../components/results/ExecutiveSummary'
import NeuralOverlay from '../components/effects/NeuralOverlay'
import { getReport, getPdfUrl } from '../api/api'
import { getDemoReport } from '../utils/demoData'
import {
  getRadarData, computeConsensus, scoreColor,
} from '../utils/reportParser'
import type { Evaluation, ReportData } from '../types'

const AGENT_META: Record<string, { icon: ElementType; label: string; color: string }> = {
  engineering: { icon: Cpu, label: 'Engineering', color: '#A855F7' },
  innovation_scalability: { icon: TrendingUp, label: 'Innovation & Scale', color: '#14B8A6' },
  ppt: { icon: Star, label: 'Presentation', color: '#A78BFA' },
  risk_impact: { icon: Globe, label: 'Risk & Impact', color: '#10B981' },
  risk: { icon: Globe, label: 'Risk & Impact', color: '#10B981' },
  chief_evaluation: { icon: Shield, label: 'Chief Evaluation', color: '#F59E0B' },
  technical: { icon: Cpu, label: 'Technical', color: '#A855F7' },
  security: { icon: Lock, label: 'Security', color: '#EF4444' },
  presentation: { icon: Star, label: 'Presentation', color: '#A78BFA' },
  innovation: { icon: Zap, label: 'Innovation', color: '#F59E0B' },
  impact: { icon: Globe, label: 'Impact', color: '#10B981' },
  failure: { icon: AlertTriangle, label: 'Failure Risk', color: '#F97316' },
  scalability: { icon: TrendingUp, label: 'Scalability', color: '#14B8A6' },
  cross_exam: { icon: Activity, label: 'Cross Exam', color: '#8B5CF6' },
}

function AgentCard({ agentKey, evaluation }: { agentKey: string; evaluation: Evaluation }) {
  const [expanded, setExpanded] = useState(false)
  const meta = AGENT_META[agentKey] || { icon: Shield, label: agentKey, color: '#64748B' }
  const Icon = meta.icon
  const score = evaluation.score ?? 0

  return (
    <motion.div className="glass-card" layout>
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ background: `${meta.color}20` }}
          >
            <Icon size={18} style={{ color: meta.color }} />
          </div>
          <div>
            <h3 className="font-display font-semibold text-sentinel-text">{meta.label}</h3>
            {evaluation.score !== null && (
              <div className="flex items-center gap-2 mt-1">
                <div className="h-1.5 w-24 bg-sentinel-border rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: scoreColor(score) }}
                    initial={{ width: 0 }}
                    animate={{ width: `${score}%` }}
                    transition={{ duration: 1.2 }}
                  />
                </div>
                <span className="text-xs font-mono" style={{ color: scoreColor(score) }}>
                  {score.toFixed(0)}/100
                </span>
              </div>
            )}
          </div>
        </div>
        {expanded ? <ChevronUp size={16} className="text-sentinel-muted" /> : <ChevronDown size={16} className="text-sentinel-muted" />}
      </div>

      {expanded && evaluation.findings && (
        <motion.div
          className="mt-4 pt-4 border-t border-white/5"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
        >
          <pre className="text-xs text-sentinel-muted whitespace-pre-wrap font-mono leading-relaxed max-h-80 overflow-y-auto">
            {evaluation.findings}
          </pre>
        </motion.div>
      )}
    </motion.div>
  )
}

interface ReportPageProps {
  demo?: boolean
}

export default function ReportPage({ demo = false }: ReportPageProps) {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [verdictRevealed, setVerdictRevealed] = useState(demo)

  useEffect(() => {
    if (demo) {
      setReport(getDemoReport())
      setLoading(false)
      return
    }
    if (!projectId) return
    getReport(projectId)
      .then(data => {
        setReport(data)
        setLoadError(null)
        setLoading(false)
      })
      .catch((err: unknown) => {
        const code = (err as { code?: string })?.code
        const message = err instanceof Error ? err.message : 'Failed to load report'
        setLoadError(code === 'EVALUATION_INCOMPLETE' ? 'Evaluation still in progress…' : message)
        setLoading(false)
      })
  }, [projectId, demo])

  if (loading) {
    return (
      <AppShell>
        <div className="min-h-[70vh] flex items-center justify-center">
          <div className="text-center">
            <motion.div
              className="w-14 h-14 border-2 border-violet-400 border-t-transparent rounded-full mx-auto mb-4"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <p className="text-sentinel-muted font-mono text-sm">Loading intelligence report...</p>
          </div>
        </div>
      </AppShell>
    )
  }

  if (!report) {
    return (
      <AppShell>
        <div className="min-h-[70vh] flex items-center justify-center text-center px-4">
          <div>
            <p className="text-red-400 mb-2 font-display font-semibold">
              {loadError?.includes('in progress') ? 'Evaluation In Progress' : 'Failed to Load Report'}
            </p>
            <p className="text-sentinel-muted text-sm mb-4">{loadError}</p>
            <button onClick={() => navigate('/')} className="sentinel-btn-primary">Go Home</button>
          </div>
        </div>
      </AppShell>
    )
  }

  const vd = report.verdict_data
  const overallScore = report.overall_score ?? vd?.overall_score ?? 0
  const verdict = (report.verdict ?? vd?.verdict ?? 'IMPROVE') as string
  const radarData = getRadarData(vd?.agent_scores)
  const consensus = computeConsensus(vd?.agent_scores)
  const confidence = vd?.confidence ?? 0
  const riskLevel = vd?.risk_level ?? 'MEDIUM'
  const heatmapCategories = radarData.map(d => ({ label: d.subject, score: d.score }))
  const barData = radarData.map(d => ({ name: d.subject, score: d.score }))
  const pdfId = demo ? null : projectId

  return (
    <AppShell particles={false}>
      <NeuralOverlay />

      {/* Header */}
      <div className="border-b border-white/5 bg-sentinel-bg/60 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <button
            onClick={() => navigate(demo ? '/' : '/submit')}
            className="flex items-center gap-1.5 text-sentinel-muted hover:text-sentinel-text transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            <span className="font-display">{demo ? 'Back to Home' : 'New Evaluation'}</span>
          </button>
          {pdfId && report.report_status !== 'failed' && (
            <a
              href={getPdfUrl(pdfId)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 glass-pill px-4 py-2 text-violet-300 hover:bg-white/10 transition-colors text-sm font-display"
            >
              <Download size={15} />
              <span className="hidden sm:inline">Download PDF</span>
            </a>
          )}
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-10">
        {report.report_status === 'failed' && (
          <motion.div
            className="glass-card border border-amber-500/25 px-4 py-3 text-sm"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <p className="text-amber-300 font-display font-semibold">Report Generation Failed</p>
            <p className="text-sentinel-muted text-xs mt-1 font-mono">
              {report.report_error || 'PDF export failed — scores and verdict below are still valid.'}
            </p>
          </motion.div>
        )}

        {/* Title */}
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <p className="text-xs font-mono text-sentinel-muted uppercase tracking-[0.3em] mb-2">
            Deployment Readiness Report
          </p>
          <h1 className="text-3xl sm:text-5xl font-display font-bold text-sentinel-text mb-2">
            {report.project_name}
          </h1>
          <p className="text-sm text-violet-300 font-mono">{report.project_type ?? vd?.project_type}</p>
          {demo && (
            <span className="inline-block mt-2 text-xs font-mono text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full">
              DEMO MODE
            </span>
          )}
        </motion.div>

        {/* Verdict reveal */}
        <VerdictReveal
          verdict={verdict}
          onRevealed={() => setVerdictRevealed(true)}
        />

        {verdictRevealed && (
          <motion.div
            className="space-y-10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
          >
            {/* Top metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass-card flex flex-col items-center py-8 sm:col-span-2 lg:col-span-1">
                <ScoreRing score={overallScore} size={160} label="Overall Score" />
              </div>
              <ConfidenceMeter value={confidence} />
              <AgentConsensus score={consensus} />
              <ReadinessGauge score={overallScore} />
            </div>

            <div className="glass-card">
              <h2 className="font-display font-bold text-xl mb-4">Evaluation Context</h2>
              <p className="text-sm text-sentinel-muted mb-2"><span className="text-sentinel-text">Project Type:</span> {vd?.project_type ?? report.project_type}</p>
              <p className="text-sm text-sentinel-muted mb-4"><span className="text-sentinel-text">Evaluation Standard:</span> {vd?.evaluation_standard}</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(vd?.scoring_weights ?? {}).map(([name, weight]) => (
                  <span key={name} className="glass-pill px-3 py-1 text-xs font-mono text-violet-300">
                    {name.replace('_', ' ')} {Math.round(weight * 100)}%
                  </span>
                ))}
              </div>
            </div>

            <div className="glass-card border border-amber-500/20">
              <h2 className="font-display font-bold text-xl mb-4">Why did this project receive this score?</h2>
              <p className="text-sm text-sentinel-muted mb-3">Calibration: <span className="text-amber-300">{vd?.score_band}</span></p>
              <div className="grid md:grid-cols-3 gap-4 text-sm">
                <div><h3 className="text-emerald-300 mb-2">Positive factors</h3>{(vd?.positive_factors ?? []).map(x => <p key={x} className="text-sentinel-muted mb-1">+ {x}</p>)}</div>
                <div><h3 className="text-amber-300 mb-2">Penalties</h3>{(vd?.penalties ?? []).map(x => <p key={x.factor} className="text-sentinel-muted mb-1">-{x.points} {x.factor}</p>)}</div>
                <div><h3 className="text-red-300 mb-2">Missing evidence</h3>{(vd?.missing_evidence ?? []).map(x => <p key={x} className="text-sentinel-muted mb-1">{x}</p>)}</div>
              </div>
            </div>

            {/* Analytics row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="glass-card lg:col-span-2">
                <h3 className="text-xs font-mono text-sentinel-muted uppercase tracking-widest mb-4">
                  Agent Score Radar
                </h3>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#1E2D45" />
                    <PolarAngleAxis
                      dataKey="subject"
                      tick={{ fill: '#64748B', fontSize: 11, fontFamily: 'Space Grotesk' }}
                    />
                    <Radar
                      name="Score"
                      dataKey="score"
                      stroke="#EC4899"
                      fill="#EC4899"
                      fillOpacity={0.25}
                      strokeWidth={2}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
              <ThreatRadar riskLevel={riskLevel} />
            </div>

            {/* Bar chart + heatmap */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="glass-card">
                <h3 className="text-xs font-mono text-sentinel-muted uppercase tracking-widest mb-6">
                  Score Distribution
                </h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={barData} barSize={28}>
                    <XAxis dataKey="name" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fill: '#64748B', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#0D1526', border: '1px solid #1E2D45', borderRadius: 8 }}
                      labelStyle={{ color: '#E2E8F0' }}
                    />
                    <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                      {barData.map(entry => (
                        <Cell key={entry.name} fill={scoreColor(entry.score)} fillOpacity={0.85} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <RiskHeatmap categories={heatmapCategories} />
            </div>

            {/* Cross-examination */}
            {vd?.contradictions && vd.contradictions.length > 0 && (
              <div className="glass-card border border-purple-500/20 p-5">
                <h3 className="text-xs font-mono text-purple-300 uppercase tracking-widest mb-3">
                  Chief Cross-Examination
                </h3>
                <ul className="space-y-2">
                  {vd.contradictions.map((c, i) => (
                    <li key={i} className="text-sm text-sentinel-muted flex gap-2">
                      <span className="text-purple-400">⚡</span> {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Executive summary */}
            {vd && <ExecutiveSummary data={vd} />}

            {/* Agent details */}
            <div>
              <h2 className="font-display font-bold text-xl text-sentinel-text mb-6">
                Detailed Agent Reports
              </h2>
              <div className="space-y-3">
                {Object.entries(report.evaluations).map(([key, ev]) => (
                  <AgentCard key={key} agentKey={key} evaluation={ev} />
                ))}
              </div>
            </div>

            {/* PDF CTA */}
            {pdfId && (
              <div className="glass-card text-center py-12 border border-violet-500/10">
                <Shield size={40} className="mx-auto mb-4 text-sentinel-accent" />
                <h3 className="font-display font-bold text-xl text-sentinel-text mb-2">
                  Export Full Intelligence Report
                </h3>
                <p className="text-sentinel-muted mb-6 text-sm max-w-md mx-auto">
                  Download the complete PDF with executive summary, agent findings,
                  failure predictions, and deployment roadmap.
                </p>
                <a
                  href={getPdfUrl(pdfId)}
                  target="_blank"
                  rel="noreferrer"
                  className="sentinel-btn-primary inline-flex items-center gap-2"
                >
                  <Download size={18} />
                  Download PDF Report
                </a>
              </div>
            )}
          </motion.div>
        )}
      </main>
    </AppShell>
  )
}

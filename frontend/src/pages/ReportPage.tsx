import { useCallback, useEffect, useState, type ElementType, type ReactNode } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { motion } from 'framer-motion'
import {
  Download, ArrowLeft, Shield, ChevronDown, ChevronUp,
  Cpu, Lock, Star, Zap, Globe, AlertTriangle, TrendingUp, Activity,
  Fingerprint, Scale, Trophy, Sparkles, Gauge, CheckCircle2,
  LayoutDashboard, BarChart3, FileText, Map, Menu, PanelLeftClose,
  PanelLeftOpen, X, Wrench,
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
import { phaseDeploymentRoadmap } from '../utils/listNormalizer'
import type { Evaluation, RankingData, ReportData } from '../types'

const AGENT_META: Record<string, { icon: ElementType; label: string; color: string }> = {
  forge: { icon: Cpu, label: 'Forge', color: '#00E5FF' },
  sentinel: { icon: Lock, label: 'Sentinel', color: '#EF4444' },
  visionary: { icon: Zap, label: 'Visionary', color: '#00FFA3' },
  showcase: { icon: Star, label: 'Showcase', color: '#7C3AED' },
  guardian: { icon: Globe, label: 'Guardian', color: '#00FFA3' },
  yowon_prime: { icon: Shield, label: 'YOWON Prime', color: '#7C3AED' },
  engineering: { icon: Cpu, label: 'Forge', color: '#00E5FF' },
  innovation_scalability: { icon: TrendingUp, label: 'Visionary', color: '#00FFA3' },
  ppt: { icon: Star, label: 'Showcase', color: '#7C3AED' },
  risk_impact: { icon: Globe, label: 'Guardian', color: '#00FFA3' },
  risk: { icon: Globe, label: 'Guardian', color: '#00FFA3' },
  chief_evaluation: { icon: Shield, label: 'YOWON Prime', color: '#7C3AED' },
  technical: { icon: Cpu, label: 'Forge', color: '#00E5FF' },
  security: { icon: Lock, label: 'Sentinel', color: '#EF4444' },
  presentation: { icon: Star, label: 'Showcase', color: '#7C3AED' },
  innovation: { icon: Zap, label: 'Visionary', color: '#00FFA3' },
  impact: { icon: Globe, label: 'Guardian', color: '#00FFA3' },
  failure: { icon: AlertTriangle, label: 'Failure Risk', color: '#F97316' },
  scalability: { icon: TrendingUp, label: 'Scalability', color: '#00E5FF' },
  cross_exam: { icon: Activity, label: 'Cross Exam', color: '#7C3AED' },
}

const REPORT_SECTIONS: Array<{ id: string; label: string; icon: ElementType }> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'project-dna', label: 'Project DNA', icon: Fingerprint },
  { id: 'rankings', label: 'Rankings', icon: Trophy },
  { id: 'evaluation-context', label: 'Evaluation Context', icon: FileText },
  { id: 'code-intelligence', label: 'Code Intelligence', icon: Cpu },
  { id: 'repository-analysis', label: 'Repository Analysis', icon: Gauge },
  { id: 'security', label: 'Sentinel', icon: Shield },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'agent-reports', label: 'Agent Reports', icon: Activity },
  { id: 'recommendations', label: 'Recommendations', icon: Wrench },
  { id: 'deployment-roadmap', label: 'Deployment Roadmap', icon: Map },
]

const QUICK_ACTIONS = [
  { id: 'security', label: 'Jump to Sentinel', icon: Shield },
  { id: 'agent-reports', label: 'Jump to Agent Reports', icon: Activity },
  { id: 'recommendations', label: 'Jump to Recommendations', icon: Wrench },
  { id: 'deployment-roadmap', label: 'Jump to Roadmap', icon: Map },
]

function hasRankingValue(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value)
}

function rankText(rank?: string) {
  return rank && rank !== 'Insufficient Data' ? rank : 'Insufficient Data'
}

function isPresentationEnabled(projectType?: string) {
  return projectType === 'Hackathon Project'
}

function ProjectDNA({ data }: { data: { subject: string; score: number }[] }) {
  const items = data.length ? data.slice(0, 6) : [
    { subject: 'Evidence', score: 30 },
    { subject: 'Architecture', score: 30 },
    { subject: 'Sentinel', score: 30 },
  ]
  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display font-bold text-lg">Project DNA</h3>
        <Fingerprint size={18} className="text-cyan-300" />
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        {items.map(item => (
          <div key={item.subject} className="rounded-xl bg-white/[0.035] border border-white/10 p-3">
            <div className="flex justify-between text-xs mb-2">
              <span className="text-yowon-muted">{item.subject}</span>
              <span className="font-mono text-cyan-300">{Math.round(item.score)}</span>
            </div>
            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-emerald-300"
                initial={{ width: 0 }}
                animate={{ width: `${item.score}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function BenchmarkComparison({ score, consensus, ranking }: { score: number; consensus: number; ranking?: RankingData }) {
  const globalPercentile = hasRankingValue(ranking?.global_percentile) ? ranking?.global_percentile ?? 0 : null
  const categoryPercentile = hasRankingValue(ranking?.category_percentile) ? ranking?.category_percentile ?? 0 : null
  const rows = [
    { label: 'Global Percentile', value: globalPercentile },
    { label: 'Category Percentile', value: categoryPercentile },
    { label: 'This Project', value: score },
    { label: 'Agent Consensus', value: consensus },
  ]
  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display font-bold text-lg">Benchmark Comparison</h3>
        <Scale size={18} className="text-emerald-300" />
      </div>
      <div className="space-y-3">
        {rows.map(row => (
          <div key={row.label}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-yowon-muted">{row.label}</span>
              <span className="font-mono text-yowon-text">
                {row.value === null ? 'Insufficient Data' : `${Math.round(row.value)}/100`}
              </span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-300"
                style={{ width: `${row.value ?? 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-yowon-muted mt-4 font-mono">
        Compared against {ranking?.projects_compared ?? 0} historical projects.
      </p>
    </div>
  )
}

function ReadinessLadder({ score }: { score: number }) {
  const stages = ['Evidence', 'Prototype', 'Validated', 'Deployable', 'Enterprise Ready']
  const active = Math.min(stages.length - 1, Math.floor(score / 20))
  return (
    <div className="glass-card">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display font-bold text-lg">Readiness Ladder</h3>
        <Gauge size={18} className="text-cyan-300" />
      </div>
      <div className="space-y-2">
        {stages.map((stage, index) => (
          <div key={stage} className={`flex items-center gap-3 rounded-xl border p-3 ${index <= active ? 'border-cyan-300/20 bg-cyan-300/5' : 'border-white/10 bg-white/[0.02]'}`}>
            <CheckCircle2 size={16} className={index <= active ? 'text-emerald-300' : 'text-yowon-muted'} />
            <span className="text-sm text-yowon-text">{stage}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function RecommendationEngine({ fixes = [] }: { fixes?: string[] }) {
  const items = fixes.length ? fixes.slice(0, 4) : ['Add testing evidence', 'Document deployment path', 'Strengthen security review']
  return (
    <div className="glass-card border-violet-400/20">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-display font-bold text-lg">AI Recommendation Engine</h3>
        <Sparkles size={18} className="text-violet-300" />
      </div>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={item} className="flex gap-3 rounded-xl bg-white/[0.03] border border-white/10 p-3">
            <span className="font-mono text-xs text-cyan-300">P{index + 1}</span>
            <p className="text-sm text-yowon-muted">{item}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function DashboardSection({
  id,
  title,
  icon: Icon,
  children,
  accent = 'cyan',
}: {
  id: string
  title: string
  icon: ElementType
  children: ReactNode
  accent?: 'cyan' | 'violet' | 'emerald' | 'amber' | 'red'
}) {
  const accentClass = {
    cyan: 'text-cyan-300 border-cyan-300/20',
    violet: 'text-violet-300 border-violet-400/20',
    emerald: 'text-emerald-300 border-emerald-300/20',
    amber: 'text-amber-300 border-amber-300/20',
    red: 'text-red-300 border-red-300/20',
  }[accent]

  return (
    <section id={id} className="scroll-mt-24 space-y-4">
      <div className={`flex items-center gap-3 border-l-2 pl-3 ${accentClass}`}>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.035]">
          <Icon size={17} />
        </div>
        <div>
          <p className="text-[10px] font-mono uppercase tracking-[0.28em] text-yowon-muted">Report Section</p>
          <h2 className="font-display text-xl font-bold text-yowon-text">{title}</h2>
        </div>
      </div>
      {children}
    </section>
  )
}

function ReportSidebar({
  activeSection,
  collapsed,
  onToggleCollapse,
  onNavigate,
  mobile = false,
}: {
  activeSection: string
  collapsed: boolean
  onToggleCollapse: () => void
  onNavigate: (id: string) => void
  mobile?: boolean
}) {
  return (
    <aside
      className={`${mobile ? 'h-full w-[min(84vw,320px)]' : `sticky top-20 hidden h-[calc(100vh-6rem)] shrink-0 lg:block ${collapsed ? 'w-[76px]' : 'w-[260px]'}`} rounded-[8px] border border-cyan-300/10 bg-[#06101D]/88 p-3 shadow-[0_0_50px_rgba(0,229,255,0.07)] backdrop-blur-2xl`}
    >
      <div className="mb-4 flex items-center justify-between gap-2">
        {!collapsed || mobile ? (
          <div>
            <p className="text-[10px] font-mono uppercase tracking-[0.28em] text-cyan-300">YOWON AI</p>
            <p className="font-display text-sm font-semibold text-yowon-text">Results Navigator</p>
          </div>
        ) : (
          <div className="h-9 w-9 rounded-lg border border-cyan-300/20 bg-cyan-300/10" />
        )}
        {!mobile && (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-yowon-muted transition hover:border-cyan-300/30 hover:text-cyan-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            aria-label={collapsed ? 'Expand report sidebar' : 'Collapse report sidebar'}
          >
            {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          </button>
        )}
      </div>

      <nav className="space-y-1">
        {REPORT_SECTIONS.map(({ id, label, icon: Icon }) => {
          const active = activeSection === id
          return (
            <button
              key={id}
              type="button"
              onClick={() => onNavigate(id)}
              className={`group flex min-h-11 w-full items-center gap-3 rounded-[8px] border px-3 py-2 text-left transition ${
                active
                  ? 'border-cyan-300/35 bg-cyan-300/12 text-cyan-100 shadow-[0_0_20px_rgba(0,229,255,0.14)]'
                  : 'border-transparent text-yowon-muted hover:border-white/10 hover:bg-white/[0.04] hover:text-yowon-text'
              }`}
              aria-current={active ? 'true' : undefined}
            >
              <Icon size={17} className={active ? 'text-cyan-300' : 'text-yowon-muted group-hover:text-cyan-200'} />
              {(!collapsed || mobile) && (
                <span className="text-sm font-display">{label}</span>
              )}
            </button>
          )
        })}
      </nav>
    </aside>
  )
}

function DeploymentRoadmapSection({ items }: { items: string[] | string | undefined }) {
  const phases = phaseDeploymentRoadmap(items)

  return (
    <div className="glass-card border-cyan-300/15">
      {phases.length === 0 ? (
        <p className="text-sm text-yowon-muted">No deployment roadmap generated.</p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {phases.map((phase, index) => (
            <div key={phase.title} className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-300/10 text-xs font-mono text-cyan-200">
                  {index + 1}
                </span>
                <h3 className="font-display font-semibold text-yowon-text">{phase.title}</h3>
              </div>
              <div className="space-y-2">
                {phase.items.map((item, itemIndex) => (
                  <p key={`${phase.title}-${itemIndex}`} className="text-sm leading-relaxed text-yowon-muted">
                    {item}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
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
            <h3 className="font-display font-semibold text-yowon-text">{meta.label}</h3>
            {evaluation.score !== null && (
              <div className="flex items-center gap-2 mt-1">
                <div className="h-1.5 w-24 bg-yowon-border rounded-full overflow-hidden">
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
        {expanded ? <ChevronUp size={16} className="text-yowon-muted" /> : <ChevronDown size={16} className="text-yowon-muted" />}
      </div>

      {expanded && evaluation.findings && (
        <motion.div
          className="mt-4 pt-4 border-t border-white/5"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
        >
          <pre className="text-xs text-yowon-muted whitespace-pre-wrap font-mono leading-relaxed max-h-80 overflow-y-auto">
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
  const [activeSection, setActiveSection] = useState('overview')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  // Advanced Code Intelligence Workspace States
  const [intelTab, setIntelTab] = useState('overview')
  const [treeData, setTreeData] = useState<any[]>([])
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({})
  const [archGraph, setArchGraph] = useState<any>(null)
  const [techGraph, setTechGraph] = useState<any>(null)
  const [depGraph, setDepGraph] = useState<any>(null)
  const [callGraph, setCallGraph] = useState<any>(null)
  const [metricsData, setMetricsData] = useState<any>(null)
  const [healthData, setHealthData] = useState<any>(null)
  const [heatmapData, setHeatmapData] = useState<any[]>([])
  const [heatmapMetric, setHeatmapMetric] = useState('risk')
  const [recommendationsData, setRecommendationsData] = useState<any[]>([])
  const [timelineData, setTimelineData] = useState<any[]>([])
  const [evidenceData, setEvidenceData] = useState<any[]>([])
  const [selectedFile, setSelectedFile] = useState<any>(null)
  const [zoomScale, setZoomScale] = useState(1.0)

  // Lazy-loader trigger effect
  useEffect(() => {
    if (!verdictRevealed || demo || !projectId) return
    const evalId = report?.evaluation_id || projectId

    if (intelTab === 'tree' && treeData.length === 0) {
      fetch(`/evaluations/${evalId}/repository-tree`).then(res => res.json()).then(setTreeData).catch(() => {})
    } else if (intelTab === 'architecture' && !archGraph) {
      fetch(`/evaluations/${evalId}/architecture`).then(res => res.json()).then(setArchGraph).catch(() => {})
    } else if (intelTab === 'technology' && !techGraph) {
      fetch(`/evaluations/${evalId}/technology-graph`).then(res => res.json()).then(setTechGraph).catch(() => {})
    } else if (intelTab === 'dependencies' && !depGraph) {
      fetch(`/evaluations/${evalId}/dependency-graph`).then(res => res.json()).then(setDepGraph).catch(() => {})
    } else if (intelTab === 'call-graph' && !callGraph) {
      fetch(`/evaluations/${evalId}/call-graph`).then(res => res.json()).then(setCallGraph).catch(() => {})
    } else if (intelTab === 'metrics' && !metricsData) {
      fetch(`/evaluations/${evalId}/metrics`).then(res => res.json()).then(setMetricsData).catch(() => {})
    } else if (intelTab === 'health' && !healthData) {
      fetch(`/evaluations/${evalId}/health`).then(res => res.json()).then(setHealthData).catch(() => {})
    } else if (intelTab === 'heatmap') {
      fetch(`/evaluations/${evalId}/heatmap?metric=${heatmapMetric}`).then(res => res.json()).then(setHeatmapData).catch(() => {})
    } else if (intelTab === 'recommendations' && recommendationsData.length === 0) {
      fetch(`/evaluations/${evalId}/recommendations`).then(res => res.json()).then(setRecommendationsData).catch(() => {})
    } else if (intelTab === 'timeline' && timelineData.length === 0) {
      fetch(`/evaluations/${evalId}/timeline`).then(res => res.json()).then(setTimelineData).catch(() => {})
    } else if (intelTab === 'evidence' && evidenceData.length === 0) {
      fetch(`/evaluations/${evalId}/evidence`).then(res => res.json()).then(data => setEvidenceData(data.evidence || [])).catch(() => {})
    }
  }, [intelTab, projectId, report, verdictRevealed, demo, heatmapMetric])

  const toggleFolder = (path: string) => {
    const isExpanded = !!expandedPaths[path]
    setExpandedPaths(prev => ({ ...prev, [path]: !isExpanded }))
    
    if (!isExpanded) {
      const evalId = report?.evaluation_id || projectId
      fetch(`/evaluations/${evalId}/repository-tree?path=${encodeURIComponent(path)}`)
        .then(res => res.json())
        .then(children => {
          setTreeData(prev => {
            const updateNode = (nodes: any[]): any[] => {
              return nodes.map(node => {
                if (node.path === path) {
                  return { ...node, children }
                } else if (node.children) {
                  return { ...node, children: updateNode(node.children) }
                }
                return node
              })
            }
            return updateNode(prev)
          })
        })
        .catch(() => {})
    }
  }

  const loadFileContent = (fpath: string) => {
    const evalId = report?.evaluation_id || projectId
    fetch(`/evaluations/${evalId}/file/${encodeURIComponent(fpath)}`)
      .then(res => res.json())
      .then(setSelectedFile)
      .catch(() => {})
  }

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
        setLoadError(code === 'EVALUATION_INCOMPLETE' ? 'Evaluation still in progress...' : message)
        setLoading(false)
      })
  }, [projectId, demo])

  useEffect(() => {
    if (!verdictRevealed) return

    const sections = REPORT_SECTIONS
      .map(section => document.getElementById(section.id))
      .filter((section): section is HTMLElement => Boolean(section))

    if (!sections.length) return

    const observer = new IntersectionObserver(
      entries => {
        const visible = entries
          .filter(entry => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]

        if (visible?.target.id) {
          setActiveSection(visible.target.id)
        }
      },
      { rootMargin: '-18% 0px -58% 0px', threshold: [0.08, 0.2, 0.45] },
    )

    sections.forEach(section => observer.observe(section))
    return () => observer.disconnect()
  }, [verdictRevealed])

  const scrollToSection = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setActiveSection(id)
    setMobileNavOpen(false)
  }, [])

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
            <p className="text-yowon-muted font-mono text-sm">Loading intelligence report...</p>
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
            <p className="text-yowon-muted text-sm mb-4">{loadError}</p>
            <button onClick={() => navigate('/')} className="yowon-btn-primary">Go Home</button>
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
  const ranking = vd?.ranking
  const selectedProjectType = vd?.submitted_project_type ?? report.project_type ?? vd?.project_type
  const showPresentation = isPresentationEnabled(selectedProjectType)
  const reportEvaluations = Object.entries(report.evaluations).filter(([key]) => (
    showPresentation || !['showcase', 'presentation', 'ppt'].includes(key)
  ))
  const detectedConfidence = Math.round((vd?.detected_project_confidence ?? 0) * 100)
  const heatmapCategories = radarData.map(d => ({ label: d.subject, score: d.score }))
  const barData = radarData.map(d => ({ name: d.subject, score: d.score }))
  const pdfId = demo ? null : projectId

  return (
    <AppShell particles={false}>
      <NeuralOverlay />

      {/* Header */}
      <div className="border-b border-cyan-300/10 bg-yowon-bg/75 backdrop-blur-2xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <button
            onClick={() => navigate(demo ? '/' : '/submit')}
            className="flex items-center gap-1.5 text-yowon-muted hover:text-yowon-text transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            <span className="font-display">{demo ? 'Back to Home' : 'New Evaluation'}</span>
          </button>
          {pdfId && report.report_status !== 'failed' && (
            <a
              href={getPdfUrl(pdfId)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 glass-pill px-4 py-2 text-cyan-300 hover:bg-white/10 transition-colors text-sm font-display"
            >
              <Download size={15} />
              <span className="hidden sm:inline">Download PDF</span>
            </a>
          )}
        </div>
      </div>

      <main className="mx-auto max-w-[1500px] px-4 sm:px-6 py-8 sm:py-12 space-y-10">
        {report.report_status === 'failed' && (
          <motion.div
            className="glass-card border border-amber-500/25 px-4 py-3 text-sm"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <p className="text-amber-300 font-display font-semibold">Report Generation Failed</p>
            <p className="text-yowon-muted text-xs mt-1 font-mono">
              {report.report_error || 'PDF export failed. Scores and verdict below are still valid.'}
            </p>
          </motion.div>
        )}

        {vd?.status === 'INSUFFICIENT_EVIDENCE' && (
          <motion.div
            className="glass-card border border-red-500/25 px-4 py-4 text-sm"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <p className="text-red-300 font-display font-semibold">Insufficient Evidence</p>
            <p className="text-yowon-muted text-sm mt-1">
              No meaningful project files detected. Repository cannot be evaluated.
            </p>
          </motion.div>
        )}

        {/* Title */}
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <p className="text-xs font-mono text-yowon-muted uppercase tracking-[0.3em] mb-2">
            Judge-Grade Evaluation Dashboard
          </p>
          <h1 className="text-3xl sm:text-5xl font-display font-bold text-yowon-text mb-2">
            {report.project_name}
          </h1>
          <p className="text-sm text-cyan-300 font-mono">{report.project_type ?? vd?.project_type}</p>
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
            className="relative"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
          >
            {mobileNavOpen && (
              <motion.div
                className="fixed inset-0 z-50 bg-slate-950/75 backdrop-blur-md lg:hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setMobileNavOpen(false)}
              >
                <motion.div
                  className="h-full p-3"
                  initial={{ x: -320 }}
                  animate={{ x: 0 }}
                  exit={{ x: -320 }}
                  onClick={event => event.stopPropagation()}
                >
                  <div className="mb-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => setMobileNavOpen(false)}
                      className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 bg-slate-950/80 text-cyan-100"
                      aria-label="Close report navigation"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  <ReportSidebar
                    activeSection={activeSection}
                    collapsed={false}
                    onToggleCollapse={() => undefined}
                    onNavigate={scrollToSection}
                    mobile
                  />
                </motion.div>
              </motion.div>
            )}

            <div className="mb-4 flex items-center justify-between gap-3 lg:hidden">
              <button
                type="button"
                onClick={() => setMobileNavOpen(true)}
                className="flex min-h-11 items-center gap-2 rounded-lg border border-cyan-300/20 bg-cyan-300/10 px-3 text-sm font-display text-cyan-100"
              >
                <Menu size={17} />
                Sections
              </button>
              <p className="text-xs font-mono uppercase tracking-widest text-yowon-muted">
                {REPORT_SECTIONS.find(section => section.id === activeSection)?.label ?? 'Overview'}
              </p>
            </div>

            <div className="flex items-start gap-6">
              <ReportSidebar
                activeSection={activeSection}
                collapsed={sidebarCollapsed}
                onToggleCollapse={() => setSidebarCollapsed(value => !value)}
                onNavigate={scrollToSection}
              />

              <div className="min-w-0 flex-1 space-y-8">
                <div className="glass-card border-cyan-300/10 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    {QUICK_ACTIONS.map(({ id, label, icon: Icon }) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => scrollToSection(id)}
                        className="flex min-h-10 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-xs font-display text-yowon-muted transition hover:border-cyan-300/30 hover:text-cyan-100"
                      >
                        <Icon size={14} />
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                <DashboardSection id="overview" title="Overview" icon={LayoutDashboard}>
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                    <div className="glass-card flex flex-col items-center py-8 sm:col-span-2 xl:col-span-1">
                      <ScoreRing score={overallScore} size={160} label="Overall Score" />
                    </div>
                    <ConfidenceMeter value={confidence} />
                    <AgentConsensus score={consensus} />
                    <ReadinessGauge score={overallScore} />
                  </div>
                </DashboardSection>

                <DashboardSection id="project-dna" title="Project DNA" icon={Fingerprint} accent="emerald">
                  <ProjectDNA data={radarData} />
                </DashboardSection>

                <DashboardSection id="rankings" title="Rankings" icon={Trophy} accent="violet">
                  <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    <div className="glass-card">
                      <div className="flex items-center justify-between mb-5">
                        <h3 className="font-display font-bold text-lg">Global Ranking Indicator</h3>
                        <Trophy size={18} className="text-violet-300" />
                      </div>
                      <p className="text-4xl font-display font-bold text-yowon-text">{rankText(ranking?.global_rank)}</p>
                      <p className="text-sm text-yowon-muted mt-3">
                        Compared Against: {ranking?.projects_compared ?? 0} Projects
                      </p>
                    </div>
                    <div className="glass-card">
                      <div className="flex items-center justify-between mb-5">
                        <h3 className="font-display font-bold text-lg">Category Ranking</h3>
                        <Scale size={18} className="text-emerald-300" />
                      </div>
                      <p className="text-4xl font-display font-bold text-yowon-text">{rankText(ranking?.category_rank)}</p>
                      <p className="text-sm text-yowon-muted mt-3">
                        Among {vd?.project_type ?? report.project_type ?? 'This Category'} Projects
                      </p>
                      <p className="text-xs text-yowon-muted/80 mt-1 font-mono">
                        Compared Against: {ranking?.category_projects_compared ?? 0}
                      </p>
                    </div>
                    <BenchmarkComparison score={overallScore} consensus={consensus} ranking={ranking} />
                  </div>
                </DashboardSection>

                <DashboardSection id="evaluation-context" title="Evaluation Context" icon={FileText}>
                  <div className="glass-card">
                    <p className="text-sm text-yowon-muted mb-2"><span className="text-yowon-text">Selected Project Type:</span> {selectedProjectType}</p>
                    {vd?.detected_project_type && (
                      <p className="text-sm text-yowon-muted mb-2">
                        <span className="text-yowon-text">AI Detected Type:</span> {vd.detected_project_type}
                        {detectedConfidence ? ` (${detectedConfidence}% confidence)` : ''}
                      </p>
                    )}
                    <p className="text-sm text-yowon-muted mb-2"><span className="text-yowon-text">Scoring Rubric Used:</span> {vd?.project_type ?? report.project_type}</p>
                    <p className="text-sm text-yowon-muted mb-4"><span className="text-yowon-text">Evaluation Standard:</span> {vd?.evaluation_standard}</p>
                    {vd?.project_type_justification && (
                      <p className="text-sm text-yowon-muted mb-4"><span className="text-yowon-text">Project Type Justification:</span> {vd.project_type_justification}</p>
                    )}
                    <div className="grid sm:grid-cols-3 gap-3 mb-4">
                      <div className="border border-white/5 rounded-lg p-3">
                        <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Score Band</p>
                        <p className="text-sm text-amber-300 mt-1">{vd?.score_band ?? 'Unknown'}</p>
                      </div>
                      <div className="border border-white/5 rounded-lg p-3">
                        <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Evidence Quality</p>
                        <p className="text-sm text-cyan-300 mt-1">{vd?.evidence_quality ?? 'Unknown'}</p>
                      </div>
                      <div className="border border-white/5 rounded-lg p-3">
                        <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Completeness</p>
                        <p className="text-sm text-emerald-300 mt-1">{vd?.repository_completeness_score ?? 0}/100</p>
                      </div>
                    </div>
                    {vd?.confidence_explanation && (
                      <p className="text-sm text-yowon-muted mb-4"><span className="text-yowon-text">Confidence:</span> {vd.confidence_explanation}</p>
                    )}
                    {vd?.calibration_explanation && (
                      <p className="text-sm text-yowon-muted mb-4"><span className="text-yowon-text">Calibration:</span> {vd.calibration_explanation}</p>
                    )}
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(vd?.scoring_weights ?? {}).map(([name, weight]) => (
                        <span key={name} className="glass-pill px-3 py-1 text-xs font-mono text-cyan-300">
                          {name.replace('_', ' ')} {Math.round(weight * 100)}%
                        </span>
                      ))}
                    </div>
                  </div>
                </DashboardSection>

                <DashboardSection id="code-intelligence" title="Code Intelligence" icon={Cpu} accent="emerald">
                  <div className="glass-card">
                    {vd?.architecture_summary && (
                      <p className="text-sm text-yowon-muted mb-4"><span className="text-yowon-text">Architecture:</span> {vd.architecture_summary}</p>
                    )}
                    <div className="grid md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <h3 className="text-cyan-300 mb-2">Detected Technologies</h3>
                        {(vd?.detected_technologies?.length ? vd.detected_technologies : ['None explicitly detected']).map(x => (
                          <p key={x} className="text-yowon-muted mb-1">{x}</p>
                        ))}
                      </div>
                      <div>
                        <h3 className="text-emerald-300 mb-2">Detected Algorithms</h3>
                        {(vd?.detected_algorithms?.length ? vd.detected_algorithms : ['None explicitly detected']).map(x => (
                          <p key={x} className="text-yowon-muted mb-1">{x}</p>
                        ))}
                      </div>
                      <div>
                        <h3 className="text-emerald-300 mb-2">Evidence Found</h3>
                        {(vd?.evidence_found?.length ? vd.evidence_found : ['No implementation evidence found']).map(x => (
                          <p key={x} className="text-yowon-muted mb-1">+ {x}</p>
                        ))}
                      </div>
                      <div>
                        <h3 className="text-red-300 mb-2">Evidence Missing</h3>
                        {(vd?.evidence_missing?.length ? vd.evidence_missing : ['No missing implementation evidence recorded']).map(x => (
                          <p key={x} className="text-yowon-muted mb-1">{x}</p>
                        ))}
                      </div>
                    </div>
                    <div className="mt-4 glass-pill inline-flex px-3 py-1 text-xs font-mono text-cyan-300">
                      Community Impact Score: {vd?.community_impact_score ?? 0}/100
                    </div>
                  </div>
                </DashboardSection>

                {/* ══ REPOSITORY ANALYSIS WORKSPACE ══ */}
                <DashboardSection id="repository-analysis" title="Code Intelligence Command Center" icon={Gauge} accent="amber">
                  <div className="flex flex-wrap gap-2 mb-6 border-b border-white/[0.06] pb-3">
                    {[
                      { id: 'overview', label: 'Overview' },
                      { id: 'tree', label: 'File Explorer' },
                      { id: 'architecture', label: 'Architecture' },
                      { id: 'technology', label: 'Tech Stack' },
                      { id: 'dependencies', label: 'Dependencies' },
                      { id: 'call-graph', label: 'Call Graph' },
                      { id: 'health', label: 'Health' },
                      { id: 'heatmap', label: 'Treemap Heatmap' },
                      { id: 'metrics', label: 'Metrics' },
                      { id: 'evidence', label: 'Evidence Logs' },
                      { id: 'recommendations', label: 'Action Checklist' },
                      { id: 'timeline', label: 'Timeline' }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setIntelTab(tab.id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all duration-200 border ${
                          intelTab === tab.id
                            ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.15)]'
                            : 'bg-white/[0.02] border-white/[0.05] text-yowon-muted hover:bg-white/[0.05] hover:text-white'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* 1. OVERVIEW TAB */}
                  {intelTab === 'overview' && (
                    <div className="space-y-4">
                      {vd?.repository_statistics && Object.keys(vd.repository_statistics).length > 0 ? (
                        <div className="glass-card">
                          <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Repository Statistics</p>
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {Object.entries(vd.repository_statistics).map(([name, value]) => (
                              <div key={name} className="border border-white/5 rounded-lg p-3">
                                <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">
                                  {name.replace(/_/g, ' ')}
                                </p>
                                <p className="text-lg font-mono text-white mt-1">{value}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="glass-card">
                          <p className="text-sm text-yowon-muted">No repository statistics were included in this report.</p>
                        </div>
                      )}

                      <div className="glass-card border border-amber-500/20">
                        <div className="absolute inset-0 bg-gradient-to-b from-amber-500/[0.04] to-transparent pointer-events-none rounded-[inherit]" />
                        <div className="relative z-10">
                          <p className="font-semibold text-white mb-4 text-sm" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                            Why did this project receive this score?
                          </p>
                          <p className="text-xs text-yowon-muted mb-4">
                            Calibration: <span className="text-amber-300 font-semibold">{vd?.score_band}</span>
                          </p>
                          <div className="grid md:grid-cols-3 gap-4 text-xs">
                            <div>
                              <p className="font-bold text-emerald-400 mb-2 uppercase tracking-wider text-[10px]">Positive Factors</p>
                              {(vd?.positive_factors ?? []).map(x => <p key={x} className="text-yowon-muted mb-1">+ {x}</p>)}
                            </div>
                            <div>
                              <p className="font-bold text-amber-300 mb-2 uppercase tracking-wider text-[10px]">Penalties</p>
                              <ul className="space-y-1">
                                {(vd?.penalties ?? []).map(x => (
                                  <li key={`${x.dimension}-${x.factor}`} className="text-yowon-muted flex gap-2">
                                    <span className="text-amber-300 shrink-0">−</span>
                                    {x.dimension ? `${x.dimension}: ` : ''}{x.factor}
                                    {x.points != null ? ` (-${x.points})` : ''}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <p className="font-bold text-red-400 mb-2 uppercase tracking-wider text-[10px]">Missing Evidence</p>
                              {(vd?.missing_evidence ?? []).map(x => <p key={x} className="text-yowon-muted mb-1">{x}</p>)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 2. REPOSITORY TREE TAB */}
                  {intelTab === 'tree' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-[500px]">
                      {/* Left: Interactive Tree */}
                      <div className="glass-card lg:col-span-2 overflow-y-auto max-h-[600px] font-mono text-xs">
                        <p className="text-[10px] uppercase tracking-[0.22em] text-yowon-muted mb-4">Workspace Tree Explorer</p>
                        {treeData.length === 0 ? (
                          <div className="text-yowon-muted py-8 text-center">Loading directory tree...</div>
                        ) : (
                          <div className="space-y-1 pl-1">
                            {(() => {
                              const renderNode = (node: any, depth = 0) => {
                                const isDir = node.type === 'dir'
                                const isExpanded = !!expandedPaths[node.path]
                                return (
                                  <div key={node.path} className="select-none">
                                    <div
                                      onClick={() => isDir ? toggleFolder(node.path) : loadFileContent(node.path)}
                                      className={`flex items-center gap-2 py-1 px-2 rounded hover:bg-white/[0.04] cursor-pointer transition-all ${
                                        selectedFile?.path === node.path ? 'bg-amber-500/10 text-amber-300' : ''
                                      }`}
                                      style={{ paddingLeft: `${depth * 16 + 8}px` }}
                                    >
                                      <span className="text-yowon-muted shrink-0">
                                        {isDir ? (isExpanded ? '📂' : '📁') : '📄'}
                                      </span>
                                      <span className="truncate">{node.name}</span>
                                      {!isDir && node.language && (
                                        <span className="text-[9px] bg-white/[0.05] border border-white/10 text-yowon-muted px-1.5 py-0.5 rounded shrink-0">
                                          {node.language}
                                        </span>
                                      )}
                                      {!isDir && node.size > 0 && (
                                        <span className="text-[9px] text-yowon-muted ml-auto shrink-0">
                                          {Math.round(node.size / 1024)} KB
                                        </span>
                                      )}
                                    </div>
                                    {isDir && isExpanded && node.children && (
                                      <div className="border-l border-white/[0.06] ml-[15px]">
                                        {node.children.map((c: any) => renderNode(c, depth + 1))}
                                      </div>
                                    )}
                                  </div>
                                )
                              }
                              return treeData.map(node => renderNode(node))
                            })()}
                          </div>
                        )}
                      </div>

                      {/* Right: File Code & Metrics Drawer */}
                      <div className="glass-card">
                        <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Symbol & Code Inspector</p>
                        {selectedFile ? (
                          <div className="space-y-4">
                            <div>
                              <p className="text-white font-bold truncate text-xs">{selectedFile.path.split('/').pop()}</p>
                              <p className="text-[10px] text-yowon-muted truncate">{selectedFile.path}</p>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                              <div className="bg-white/[0.02] border border-white/5 rounded px-2 py-1">
                                <span className="text-yowon-muted block">Lines (LOC)</span>
                                <span className="text-amber-300 font-bold text-sm">{selectedFile.metrics?.loc || 0}</span>
                              </div>
                              <div className="bg-white/[0.02] border border-white/5 rounded px-2 py-1">
                                <span className="text-yowon-muted block">Complexity</span>
                                <span className="text-cyan-300 font-bold text-sm">
                                  {selectedFile.metrics?.complexity?.cyclomatic_complexity || 1}
                                </span>
                              </div>
                            </div>

                            {/* Triggered Rules evidence */}
                            {selectedFile.evidence && selectedFile.evidence.length > 0 && (
                              <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-2.5 space-y-2">
                                <p className="text-[10px] font-mono font-bold text-red-400 uppercase tracking-wider">Traced Vulnerabilities / Rules</p>
                                {selectedFile.evidence.map((ev: any) => (
                                  <div key={ev.rule_id} className="text-[11px] leading-normal text-red-300">
                                    <p className="font-bold">{ev.rule_id}</p>
                                    <p className="text-yowon-muted">Line {ev.line_start}-{ev.line_end} (Confidence: {Math.round(ev.confidence * 100)}%)</p>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Snippet Preview */}
                            <div className="bg-black/40 border border-white/10 rounded-lg p-3 font-mono text-[10px] overflow-x-auto max-h-[300px] leading-relaxed text-slate-300">
                              <pre><code>{selectedFile.content}</code></pre>
                            </div>
                          </div>
                        ) : (
                          <div className="text-yowon-muted text-xs py-12 text-center">
                            Select a source file in the explorer tree to inspect its AST elements and metrics.
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 3. DYNAMIC ARCHITECTURE GRAPH TAB */}
                  {intelTab === 'architecture' && (
                    <div className="glass-card min-h-[500px]">
                      <div className="flex justify-between items-center mb-4">
                        <div>
                          <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted">Pipeline Architecture Topology</p>
                          <p className="text-xs text-white mt-1">Inferred runtime blocks and sequential connection flows.</p>
                        </div>
                        <div className="flex gap-2">
                          <button onClick={() => setZoomScale(s => Math.max(0.6, s - 0.1))} className="px-2 py-1 bg-white/[0.04] border border-white/10 rounded text-xs">-</button>
                          <button onClick={() => setZoomScale(s => Math.min(2.0, s + 0.1))} className="px-2 py-1 bg-white/[0.04] border border-white/10 rounded text-xs">+</button>
                          <button onClick={() => setZoomScale(1.0)} className="px-2 py-1 bg-white/[0.04] border border-white/10 rounded text-xs">Reset</button>
                        </div>
                      </div>

                      {archGraph ? (
                        <div className="relative overflow-hidden bg-black/30 border border-white/5 rounded-xl min-h-[400px] flex items-center justify-center">
                          <div
                            className="flex flex-wrap gap-12 justify-center items-center p-8 transition-transform duration-200"
                            style={{ transform: `scale(${zoomScale})` }}
                          >
                            {archGraph.nodes.map((node: any) => (
                              <motion.div
                                key={node.id}
                                whileHover={{ scale: 1.05 }}
                                className="bg-yowon-bg/95 border border-cyan-500/30 rounded-xl p-4 w-44 shadow-2xl backdrop-blur relative z-10"
                              >
                                <span className="text-[9px] font-mono text-cyan-400 uppercase tracking-widest block mb-1">
                                  {node.type.toUpperCase()}
                                </span>
                                <h4 className="text-xs font-bold text-white mb-2">{node.label}</h4>
                                <p className="text-[10px] text-yowon-muted leading-snug">{node.metadata?.description}</p>
                                
                                {node.metadata?.technologies && node.metadata.technologies.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-3">
                                    {node.metadata.technologies.map((t: string) => (
                                      <span key={t} className="text-[8px] bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 px-1 rounded">
                                        {t}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </motion.div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading architecture topology graph...</div>
                      )}
                    </div>
                  )}

                  {/* 4. TECHNOLOGY TAB */}
                  {intelTab === 'technology' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Detected Technology Relations</p>
                      {techGraph ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                          {techGraph.nodes.map((node: any) => (
                            <div key={node.id} className="bg-white/[0.02] border border-white/5 rounded-xl p-4 flex items-center gap-3">
                              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center font-bold text-emerald-400">
                                {node.label.substring(0, 2).toUpperCase()}
                              </div>
                              <div>
                                <h4 className="text-xs font-bold text-white">{node.label}</h4>
                                <p className="text-[10px] text-yowon-muted mt-0.5">Stack Framework</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading technology stack nodes...</div>
                      )}
                    </div>
                  )}

                  {/* 5. DEPENDENCIES TAB */}
                  {intelTab === 'dependencies' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Code Manifest Dependencies</p>
                      {depGraph ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                          {depGraph.nodes.filter((n: any) => n.type === 'dependency').map((node: any) => (
                            <div key={node.id} className="bg-white/[0.02] border border-white/5 rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-xs font-mono font-bold text-white truncate">{node.label.split('@')[0]}</span>
                              <span className="text-[10px] text-yowon-muted font-mono mt-2">
                                Version: <span className="text-cyan-400 font-bold">{node.metadata?.version || 'unknown'}</span>
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading dependency list...</div>
                      )}
                    </div>
                  )}

                  {/* 6. CALL GRAPH TAB */}
                  {intelTab === 'call-graph' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Inter-Module Imports Call Graph</p>
                      {callGraph ? (
                        <div className="bg-black/20 border border-white/5 rounded-xl p-4 overflow-y-auto max-h-[600px] font-mono text-xs">
                          {callGraph.edges.length === 0 ? (
                            <p className="text-yowon-muted text-center py-12">No inter-module imports detected in parsed source code files.</p>
                          ) : (
                            <div className="space-y-3">
                              {callGraph.edges.map((edge: any) => (
                                <div key={`${edge.source}-${edge.target}`} className="flex items-center gap-3 bg-white/[0.02] border border-white/5 p-3 rounded-lg">
                                  <span className="text-amber-300 font-semibold truncate">{edge.source.split('/').pop()}</span>
                                  <span className="text-yowon-muted text-[10px]">⎯ imports ⎯➔</span>
                                  <span className="text-cyan-300 font-semibold truncate">{edge.target.split('/').pop()}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading module call graph...</div>
                      )}
                    </div>
                  )}

                  {/* 7. HEALTH TAB */}
                  {intelTab === 'health' && (
                    <div className="space-y-4">
                      {healthData ? (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {[
                            { name: 'Documentation', score: healthData.documentation, desc: 'README quality and comment ratio.', color: '#00FFA3' },
                            { name: 'Testing', score: healthData.testing, desc: 'Test coverage and frameworks.', color: '#00E5FF' },
                            { name: 'Security', score: healthData.security, desc: 'Credentials and API exposures.', color: '#EF4444' },
                            { name: 'Deployment', score: healthData.deployment, desc: 'Dockerfiles and pipeline actions.', color: '#7C3AED' },
                            { name: 'Architecture', score: healthData.architecture, desc: 'Modularity and folder separation.', color: '#F59E0B' },
                            { name: 'Maintainability', score: healthData.maintainability, desc: 'Complexity and comment balance.', color: '#22D3EE' }
                          ].map(h => (
                            <div key={h.name} className="glass-card flex flex-col justify-between">
                              <div>
                                <h4 className="font-bold text-white text-xs mb-1">{h.name}</h4>
                                <p className="text-[10px] text-yowon-muted mb-4">{h.desc}</p>
                              </div>
                              <div className="flex items-center gap-4">
                                <div className="text-2xl font-black font-mono" style={{ color: h.color }}>
                                  {h.score}/100
                                </div>
                                <div className="w-full bg-white/[0.04] h-2 rounded-full overflow-hidden border border-white/5">
                                  <div className="h-full rounded-full" style={{ width: `${h.score}%`, backgroundColor: h.color }} />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading health scores...</div>
                      )}
                    </div>
                  )}

                  {/* 8. HEATMAP TAB */}
                  {intelTab === 'heatmap' && (
                    <div className="glass-card min-h-[500px]">
                      <div className="flex justify-between items-center mb-6">
                        <div>
                          <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted">Interactive Treemap Heatmap</p>
                          <p className="text-xs text-white mt-1">Files sized by volume and colored by selected risk metric.</p>
                        </div>
                        <div className="flex gap-2">
                          {['risk', 'importance', 'complexity', 'coverage'].map(m => (
                            <button
                              key={m}
                              onClick={() => setHeatmapMetric(m)}
                              className={`px-2 py-1 text-[10px] rounded font-mono border ${
                                heatmapMetric === m
                                  ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                                  : 'bg-white/[0.02] border-white/10 text-yowon-muted hover:bg-white/[0.05]'
                              }`}
                            >
                              {m.toUpperCase()}
                            </button>
                          ))}
                        </div>
                      </div>

                      {heatmapData.length > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
                          {heatmapData.map(node => {
                            const isHigh = node.metric_value > 70
                            const isMed = node.metric_value > 30
                            const bgColor = heatmapMetric === 'coverage'
                              ? (node.metric_value > 50 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)')
                              : (isHigh ? 'rgba(239, 68, 68, 0.15)' : isMed ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 229, 255, 0.05)')
                            
                            const borderColor = heatmapMetric === 'coverage'
                              ? (node.metric_value > 50 ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)')
                              : (isHigh ? 'rgba(239, 68, 68, 0.4)' : isMed ? 'rgba(245, 158, 11, 0.4)' : 'rgba(255, 255, 255, 0.1)')
                            
                            const textColor = heatmapMetric === 'coverage'
                              ? (node.metric_value > 50 ? 'text-emerald-400' : 'text-red-400')
                              : (isHigh ? 'text-red-400' : isMed ? 'text-amber-400' : 'text-cyan-400')

                            return (
                              <div
                                key={node.path}
                                onClick={() => { setIntelTab('tree'); loadFileContent(node.path) }}
                                className="p-3 rounded-lg border transition-all duration-200 hover:scale-[1.02] cursor-pointer flex flex-col justify-between min-h-[90px]"
                                style={{ backgroundColor: bgColor, borderColor: borderColor }}
                              >
                                <span className="text-[10px] text-white font-bold truncate block">{node.name}</span>
                                <div className="mt-4 flex justify-between items-center">
                                  <span className="text-[9px] text-yowon-muted font-mono">VAL</span>
                                  <span className={`text-[11px] font-black font-mono ${textColor}`}>{node.metric_value}</span>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading file heatmap grid...</div>
                      )}
                    </div>
                  )}

                  {/* 9. METRICS TAB */}
                  {intelTab === 'metrics' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Static Code Metrics Logs</p>
                      {metricsData ? (
                        <div className="overflow-x-auto">
                          <table className="w-full font-mono text-[10px] text-left border-collapse">
                            <thead>
                              <tr className="border-b border-white/10 text-yowon-muted">
                                <th className="pb-2">FILE PATH</th>
                                <th className="pb-2">LOC</th>
                                <th className="pb-2">CYCLOMATIC</th>
                                <th className="pb-2">COGNITIVE</th>
                                <th className="pb-2">MAINTAINABILITY</th>
                                <th className="pb-2">RISK</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(metricsData.metrics).map(([path, data]: any) => (
                                <tr key={path} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                                  <td className="py-2 text-white truncate max-w-[250px]">{path}</td>
                                  <td className="py-2 text-cyan-400 font-bold">{data.loc}</td>
                                  <td className="py-2 text-slate-300">{data.complexity?.cyclomatic_complexity}</td>
                                  <td className="py-2 text-slate-300">{data.complexity?.cognitive_complexity}</td>
                                  <td className="py-2 text-emerald-400 font-bold">{Math.round(data.complexity?.maintainability_index)}%</td>
                                  <td className="py-2 text-red-400 font-bold">{data.risk}/100</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading code metrics...</div>
                      )}
                    </div>
                  )}

                  {/* 10. EVIDENCE TAB */}
                  {intelTab === 'evidence' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Underlying Evidence Logs</p>
                      <div className="space-y-2 max-h-[600px] overflow-y-auto">
                        {evidenceData.length === 0 ? (
                          <div className="text-yowon-muted py-12 text-center text-xs">No evidence records are available.</div>
                        ) : (
                          evidenceData.map((ev, idx) => (
                            <div key={idx} className="bg-white/[0.02] border border-white/5 rounded-lg p-3 flex justify-between items-center">
                              <div>
                                <span className="text-[9px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
                                  {ev.rule_id}
                                </span>
                                <p className="text-white text-xs font-bold mt-2">{ev.symbol_name ? `Symbol: ${ev.symbol_name}` : 'Feature detection'}</p>
                                <p className="text-[10px] text-yowon-muted font-mono mt-1">
                                  {ev.file_path} at line {ev.line_start}-{ev.line_end}
                                </p>
                              </div>
                              <div className="text-right">
                                <span className="text-[9px] text-yowon-muted font-mono block">CONFIDENCE</span>
                                <span className="text-emerald-400 font-bold font-mono text-xs">{Math.round(ev.confidence * 100)}%</span>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                  {/* 11. RECOMMENDATIONS TAB */}
                  {intelTab === 'recommendations' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Actionable Checklist Recommendations</p>
                      <div className="space-y-3">
                        {recommendationsData.length === 0 ? (
                          <div className="text-yowon-muted py-12 text-center text-xs">No check recommendations were produced.</div>
                        ) : (
                          recommendationsData.map((rec, idx) => (
                            <div key={idx} className="bg-white/[0.02] border border-white/5 rounded-xl p-4 flex justify-between gap-4">
                              <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                  <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded border ${
                                    rec.severity === 'CRITICAL' || rec.severity === 'HIGH'
                                      ? 'bg-red-500/10 border-red-500/25 text-red-400'
                                      : 'bg-amber-500/10 border-amber-500/25 text-amber-400'
                                  }`}>
                                    {rec.severity}
                                  </span>
                                  <span className="text-[9px] text-yowon-muted font-mono">EFFORT: {rec.estimated_effort}</span>
                                </div>
                                <h4 className="text-xs font-bold text-white">{rec.title}</h4>
                                <p className="text-[11px] text-yowon-muted leading-relaxed">{rec.recommendation}</p>
                              </div>
                              
                              <div className="text-right shrink-0">
                                <span className="text-[9px] text-yowon-muted font-mono block">SCORE GAIN</span>
                                <span className="text-emerald-400 font-black font-mono text-base">+{rec.expected_score_gain}</span>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                  {/* 12. TIMELINE TAB */}
                  {intelTab === 'timeline' && (
                    <div className="glass-card min-h-[500px]">
                      <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-6">Repository Evolution Timeline</p>
                      {timelineData.length > 0 ? (
                        <div className="relative pl-6 border-l border-white/[0.06] space-y-6 ml-2 font-mono text-xs">
                          {timelineData.map((snap: any, idx: number) => (
                            <div key={snap.snapshot_id} className="relative">
                              {/* Bullet dot */}
                              <div className="absolute -left-[30px] top-1.5 w-4 h-4 rounded-full border border-amber-500 bg-yowon-bg flex items-center justify-center">
                                <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                              </div>

                              <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 max-w-lg">
                                <span className="text-[10px] text-yowon-muted block">{new Date(snap.timestamp).toLocaleString()}</span>
                                <p className="text-white font-bold mt-2">Commit SHA: {snap.commit_sha.substring(0, 7)}</p>
                                
                                {snap.evaluation_id && (
                                  <div className="mt-3 flex gap-4 text-[10px]">
                                    <span className="text-yowon-muted">
                                      Verdict: <span className="text-amber-400 font-bold">{snap.verdict}</span>
                                    </span>
                                    <span className="text-yowon-muted">
                                      Score: <span className="text-cyan-400 font-bold">{snap.score}/100</span>
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-yowon-muted text-xs py-24 text-center">Loading snapshot timeline history...</div>
                      )}
                    </div>
                  )}
                </DashboardSection>

                <DashboardSection id="security" title="Sentinel" icon={Shield} accent="red">
                  <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                    <ThreatRadar riskLevel={riskLevel} />
                    <div className="glass-card xl:col-span-2">
                      <h3 className="font-display font-bold text-lg mb-4">Sentinel Signal</h3>
                      <div className="grid sm:grid-cols-3 gap-3">
                        <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                          <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Risk Level</p>
                          <p className="mt-2 font-display text-xl font-bold text-red-300">{riskLevel}</p>
                        </div>
                        <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                          <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Sentinel Score</p>
                          <p className="mt-2 font-display text-xl font-bold text-cyan-300">
                            {Math.round(vd?.agent_scores?.security ?? report.evaluations.sentinel?.score ?? report.evaluations.security?.score ?? 0)}/100
                          </p>
                        </div>
                        <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                          <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Evidence Quality</p>
                          <p className="mt-2 font-display text-xl font-bold text-amber-300">{vd?.evidence_quality ?? 'Unknown'}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </DashboardSection>

                <DashboardSection id="analytics" title="Analytics" icon={BarChart3} accent="violet">
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <div className="glass-card">
                      <h3 className="text-xs font-mono text-yowon-muted uppercase tracking-widest mb-4">
                        Council Score Radar
                      </h3>
                      <ResponsiveContainer width="100%" height={260}>
                        <RadarChart data={radarData}>
                          <PolarGrid stroke="#1E2A44" />
                          <PolarAngleAxis
                            dataKey="subject"
                            tick={{ fill: '#94A3B8', fontSize: 11, fontFamily: 'Space Grotesk' }}
                          />
                          <Radar
                            name="Score"
                            dataKey="score"
                            stroke="#00E5FF"
                            fill="#00E5FF"
                            fillOpacity={0.25}
                            strokeWidth={2}
                          />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="glass-card">
                      <h3 className="text-xs font-mono text-yowon-muted uppercase tracking-widest mb-6">
                        Score Distribution
                      </h3>
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={barData} barSize={28}>
                          <XAxis dataKey="name" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
                          <YAxis domain={[0, 100]} tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
                          <Tooltip
                            contentStyle={{ background: '#0B1023', border: '1px solid #1E2A44', borderRadius: 8 }}
                            labelStyle={{ color: '#F8FAFC' }}
                          />
                          <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                            {barData.map(entry => (
                              <Cell key={entry.name} fill={scoreColor(entry.score)} fillOpacity={0.85} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="xl:col-span-2">
                      <RiskHeatmap categories={heatmapCategories} />
                    </div>
                  </div>
                </DashboardSection>

                <DashboardSection id="agent-reports" title="Agent Reports" icon={Activity}>
                  {vd?.contradictions && vd.contradictions.length > 0 && (
                    <div className="glass-card border border-purple-500/20 p-5">
                      <h3 className="text-xs font-mono text-purple-300 uppercase tracking-widest mb-3">
                        YOWON Prime Cross-Examination
                      </h3>
                      <ul className="space-y-2">
                        {vd.contradictions.map((c, i) => (
                          <li key={i} className="text-sm text-yowon-muted flex gap-2">
                            <span className="text-purple-400">!</span> {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="space-y-3">
                    {reportEvaluations.map(([key, ev]) => (
                      <AgentCard
                        key={key}
                        agentKey={key}
                        evaluation={ev}
                      />
                    ))}
                  </div>
                </DashboardSection>

                <DashboardSection id="recommendations" title="Recommendations" icon={Wrench} accent="violet">
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    <ReadinessLadder score={overallScore} />
                    <RecommendationEngine fixes={vd?.recommended_fixes} />
                  </div>
                  {vd && <ExecutiveSummary data={vd} showRoadmap={false} />}
                </DashboardSection>

                <DashboardSection id="deployment-roadmap" title="Deployment Roadmap" icon={Map}>
                  <DeploymentRoadmapSection items={vd?.roadmap ?? vd?.deployment_roadmap} />
                  {pdfId && (
                    <div className="glass-card text-center py-12 border border-violet-500/10">
                      <Shield size={40} className="mx-auto mb-4 text-yowon-primary" />
                      <h3 className="font-display font-bold text-xl text-yowon-text mb-2">
                        Export Full Intelligence Report
                      </h3>
                      <p className="text-yowon-muted mb-6 text-sm max-w-md mx-auto">
                        Download the complete PDF with executive summary, agent findings,
                        failure predictions, and deployment roadmap.
                      </p>
                      <a
                        href={getPdfUrl(pdfId)}
                        target="_blank"
                        rel="noreferrer"
                        className="yowon-btn-primary inline-flex items-center gap-2"
                      >
                        <Download size={18} />
                        Download PDF Report
                      </a>
                    </div>
                  )}
                </DashboardSection>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </AppShell>
  )
}

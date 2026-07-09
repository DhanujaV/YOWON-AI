import { useCallback, useEffect, useState, type ElementType } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Download, ArrowLeft, Shield, Cpu, Activity, Compass,
  Fingerprint, Trophy, Gauge, LayoutDashboard, BarChart3, FileText, Map, Menu, PanelLeftClose,
  PanelLeftOpen, X, Wrench,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import VerdictReveal from '../components/results/VerdictReveal'
import NeuralOverlay from '../components/effects/NeuralOverlay'
import { getReport, getPdfUrl } from '../api/api'
import { getDemoReport } from '../utils/demoData'
import { Suspense, lazy } from 'react'
import { CardSkeleton } from '../components/report/Skeletons'
import type { ReportData } from '../types'

const OverviewPanel = lazy(() => import('../components/report/OverviewPanel'))
const DNASelector = lazy(() => import('../components/report/DNASelector'))
const RankingsPanel = lazy(() => import('../components/report/RankingsPanel'))
const SentinelPanel = lazy(() => import('../components/report/SentinelPanel'))
const AnalyticsPanel = lazy(() => import('../components/report/AnalyticsPanel'))
const RecommendationsPanel = lazy(() => import('../components/report/RecommendationsPanel'))
const RoadmapPanel = lazy(() => import('../components/report/RoadmapPanel'))
const AgentReportsPanel = lazy(() => import('../components/report/AgentReportsPanel'))
const TimelinePanel = lazy(() => import('../components/report/TimelinePanel'))
const RepositoryTreePanel = lazy(() => import('../components/report/RepositoryTreePanel'))
const ArchitectureGraphPanel = lazy(() => import('../components/report/ArchitectureGraphPanel'))
const TechnologyGraphPanel = lazy(() => import('../components/report/TechnologyGraphPanel'))
const DependencyGraphPanel = lazy(() => import('../components/report/DependencyGraphPanel'))
const KnowledgeGraphPanel = lazy(() => import('../components/report/KnowledgeGraphPanel'))
const EvidenceExplorerPanel = lazy(() => import('../components/report/EvidenceExplorerPanel'))
const MetricsPanel = lazy(() => import('../components/report/MetricsPanel'))
const DiagnosticsPanel = lazy(() => import('../components/report/DiagnosticsPanel'))
const SoftwareArchitectureNavigator = lazy(() => import('../components/report/SoftwareArchitectureNavigator').then(m => ({ default: m.SoftwareArchitectureNavigator })))

const REPORT_SECTIONS: Array<{ id: string; label: string; icon: ElementType }> = [
  { id: 'software-navigator', label: 'Architecture Navigator', icon: Compass },
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'project-dna', label: 'Project DNA', icon: Fingerprint },
  { id: 'rankings', label: 'Rankings', icon: Trophy },
  { id: 'security', label: 'Sentinel', icon: Shield },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'agent-reports', label: 'Agent Reports', icon: Activity },
  { id: 'recommendations', label: 'Recommendations', icon: Wrench },
  { id: 'deployment-roadmap', label: 'Deployment Roadmap', icon: Map },
  { id: 'repository-tree', label: 'File Explorer', icon: Gauge },
  { id: 'architecture-graph', label: 'Architecture Graph', icon: Cpu },
  { id: 'technology-graph', label: 'Technology Graph', icon: Cpu },
  { id: 'dependency-graph', label: 'Dependency Graph', icon: Cpu },
  { id: 'knowledge-graph', label: 'Knowledge Graph', icon: Cpu },
  { id: 'evidence-explorer', label: 'Evidence Explorer', icon: FileText },
  { id: 'metrics', label: 'Code Metrics', icon: FileText },
  { id: 'timeline', label: 'Evaluation Timeline', icon: Activity },
  { id: 'diagnostics', label: 'Diagnostics Workspace', icon: Cpu }
]

const QUICK_ACTIONS = [
  { id: 'security', label: 'Jump to Sentinel', icon: Shield },
  { id: 'agent-reports', label: 'Jump to Agent Reports', icon: Activity },
  { id: 'recommendations', label: 'Jump to Recommendations', icon: Wrench },
  { id: 'deployment-roadmap', label: 'Jump to Roadmap', icon: Map },
]

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
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 text-yowon-muted transition hover:border-cyan-300/30 hover:text-cyan-200 focus:outline-none"
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

interface ReportPageProps {
  demo?: boolean
}

export default function ReportPage({ demo = false }: ReportPageProps) {
  const { projectId, section } = useParams<{ projectId: string, section?: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [verdictRevealed, setVerdictRevealed] = useState(demo)
  const activeSection = section || 'software-navigator'
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

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

  const scrollToSection = useCallback((id: string) => {
    navigate(`/report/${projectId}/${id}`)
    setMobileNavOpen(false)
  }, [projectId, navigate])

  if (loading) {
    return (
      <AppShell>
        <div className="min-h-[70vh] flex items-center justify-center">
          <div className="text-center">
            <motion.div
              className="w-14 h-14 border-2 border-cyan-300 border-t-transparent rounded-full mx-auto mb-4"
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
  const verdict = (report.verdict ?? vd?.verdict ?? 'IMPROVE') as string
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
            Enterprise Software Architecture Intelligence Platform
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

                <Suspense fallback={<CardSkeleton />}>
                  {activeSection === 'software-navigator' && <SoftwareArchitectureNavigator projectId={projectId || ''} />}
                  {activeSection === 'overview' && <OverviewPanel projectId={projectId || ''} />}
                  {activeSection === 'project-dna' && <DNASelector projectId={projectId || ''} />}
                  {activeSection === 'rankings' && <RankingsPanel projectId={projectId || ''} />}
                  {activeSection === 'security' && <SentinelPanel projectId={projectId || ''} />}
                  {activeSection === 'analytics' && <AnalyticsPanel projectId={projectId || ''} />}
                  {activeSection === 'agent-reports' && <AgentReportsPanel projectId={projectId || ''} />}
                  {activeSection === 'recommendations' && <RecommendationsPanel projectId={projectId || ''} />}
                  {activeSection === 'deployment-roadmap' && <RoadmapPanel projectId={projectId || ''} demo={demo} />}
                  {activeSection === 'repository-tree' && <RepositoryTreePanel projectId={projectId || ''} />}
                  {activeSection === 'architecture-graph' && <ArchitectureGraphPanel projectId={projectId || ''} />}
                  {activeSection === 'technology-graph' && <TechnologyGraphPanel projectId={projectId || ''} />}
                  {activeSection === 'dependency-graph' && <DependencyGraphPanel projectId={projectId || ''} />}
                  {activeSection === 'knowledge-graph' && <KnowledgeGraphPanel projectId={projectId || ''} />}
                  {activeSection === 'evidence-explorer' && <EvidenceExplorerPanel projectId={projectId || ''} />}
                  {activeSection === 'metrics' && <MetricsPanel projectId={projectId || ''} />}
                  {activeSection === 'timeline' && <TimelinePanel projectId={projectId || ''} demo={demo} />}
                  {activeSection === 'diagnostics' && <DiagnosticsPanel projectId={projectId || ''} />}
                </Suspense>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </AppShell>
  )
}

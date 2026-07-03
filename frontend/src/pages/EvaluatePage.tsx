import { useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Clock, CheckCircle, XCircle, Brain, Cpu, Shield, Presentation,
  Lightbulb, Globe, Gavel, Activity, Scale, Fingerprint, Trophy,
  ChevronRight, Radio,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import AgentPipelineCard from '../components/evaluation/AgentPipelineCard'
import TerminalLog from '../components/evaluation/TerminalLog'
import AgentNetwork from '../components/evaluation/AgentNetwork'
import EvaluationTimeline from '../components/evaluation/EvaluationTimeline'
import NeuralOverlay from '../components/effects/NeuralOverlay'
import { useEvaluationProgress } from '../hooks/useEvaluationProgress'
import type { AgentStatus } from '../types'

const PIPELINE = [
  { id: 'coordinator', label: 'Coordinator', desc: 'Parsing inputs and building evaluation context', icon: Brain,        color: '#00E5FF' },
  { id: 'technical',   label: 'Forge',        desc: 'Analyzing architecture and code quality',         icon: Cpu,          color: '#22D3EE' },
  { id: 'security',    label: 'Sentinel',     desc: 'Auditing OWASP risks and static scan findings',  icon: Shield,       color: '#EF4444' },
  { id: 'presentation',label: 'Showcase',     desc: 'Reviewing pitch deck and documentation',         icon: Presentation, color: '#7C3AED' },
  { id: 'innovation',  label: 'Visionary',    desc: 'Assessing novelty and scalability readiness',    icon: Lightbulb,    color: '#00FFA3' },
  { id: 'risk',        label: 'Guardian',     desc: 'Forecasting impact and failure modes',           icon: Globe,        color: '#00FFA3' },
  { id: 'chief',       label: 'YOWON Prime',  desc: 'Cross-examining the Council and rendering verdict', icon: Gavel,    color: '#7C3AED' },
]

function isPresentationEnabled(projectType?: string) {
  return projectType === 'Hackathon Project'
}

const SIMULATION_STATS = [
  { label: 'Judge Simulation', value: 'Active',  icon: Scale,       tone: 'text-cyan-300' },
  { label: 'Project DNA',      value: 'Mapping', icon: Fingerprint, tone: 'text-emerald-400' },
  { label: 'Global Rank',      value: 'Pending', icon: Trophy,      tone: 'text-violet-400' },
]

function resolveAgentStatus(
  agentId: string,
  pipeline: typeof PIPELINE,
  agentStates?: Record<string, { status: string }>,
  activeAgent?: string,
  globalStatus?: string,
): AgentStatus {
  const state = agentStates?.[agentId]
  if (state?.status === 'completed') return 'completed'
  if (state?.status === 'failed')    return 'failed'
  if (state?.status === 'running')   return 'running'
  if (globalStatus === 'done')       return 'completed'
  const normalizedActive = activeAgent === 'brief' ? 'coordinator' : activeAgent
  const idx       = pipeline.findIndex(p => p.id === agentId)
  const activeIdx = pipeline.findIndex(p => p.id === normalizedActive)
  if (activeIdx < 0)        return 'waiting'
  if (idx < activeIdx)      return 'completed'
  if (idx === activeIdx)    return 'running'
  return 'waiting'
}

export default function EvaluatePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate      = useNavigate()

  const onComplete = useCallback(
    (id: string) => setTimeout(() => navigate(`/report/${id}`), 1400),
    [navigate],
  )

  const { status, reportStatus, reportError, projectName, projectType, progress } =
    useEvaluationProgress(projectId, onComplete)

  const activeAgent    = progress.agent === 'brief' ? 'coordinator' : progress.agent
  const elapsed        = progress.elapsed_seconds  ?? 0
  const completionPct  = progress.completion_percent ?? 0

  const visiblePipeline = useMemo(
    () => PIPELINE.filter(agent => agent.id !== 'presentation' || isPresentationEnabled(projectType)),
    [projectType],
  )

  const agentStatuses = useMemo<AgentStatus[]>(() => {
    return visiblePipeline.map(p =>
      resolveAgentStatus(p.id, visiblePipeline, progress.agent_states, activeAgent, status),
    )
  }, [progress.agent_states, activeAgent, status, visiblePipeline])

  const formatTime = (s: number) => {
    const m   = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  const isDone   = status === 'done'
  const isFailed = status === 'failed'

  return (
    <AppShell particles={false}>
      <NeuralOverlay />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">

        {/* ---- Header / Status ---- */}
        <motion.div
          className="mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Status icon */}
          <div className="flex flex-col items-center text-center mb-6">
            {isDone ? (
              <motion.div
                initial={{ scale: 0 }} animate={{ scale: 1 }}
                transition={{ type: 'spring', damping: 15 }}
              >
                <CheckCircle size={52} className="text-emerald-400 mb-3"
                  style={{ filter: 'drop-shadow(0 0 16px rgba(52,211,153,0.50))' }} />
              </motion.div>
            ) : isFailed ? (
              <XCircle size={52} className="text-red-400 mb-3" />
            ) : (
              <motion.div
                className="relative w-20 h-20 mb-3"
                animate={{ boxShadow: ['0 0 20px rgba(0,229,255,0.2)', '0 0 50px rgba(0,255,163,0.34)', '0 0 20px rgba(0,229,255,0.2)'] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <div className="absolute inset-0 rounded-full border-2 border-cyan-300/20" />
                <div className="absolute inset-0 rounded-full border-2 border-t-cyan-300 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
                <div className="absolute inset-1.5 rounded-full border border-dashed border-emerald-300/15 animate-[spin_8s_linear_infinite_reverse]" />
                <Brain size={28} className="absolute inset-0 m-auto text-cyan-300" />
              </motion.div>
            )}

            <p className="text-[11px] font-mono text-cyan-300/70 uppercase tracking-[0.3em] mb-1">
              Mission Control
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold mb-2 text-white"
              style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
              {isFailed  ? 'Evaluation Failed'   :
               isDone    ? 'Evaluation Complete'  :
               'AI Jury Deliberation In Progress'}
            </h1>

            {isDone && reportStatus === 'failed' && (
              <p className="text-amber-400/80 text-xs mt-1 max-w-md">
                Verdict ready. PDF report generation failed — view results below.
              </p>
            )}
            {isDone && reportStatus === 'ready' && (
              <p className="text-emerald-400/70 text-xs mt-1 flex items-center gap-1">
                <Radio size={11} className="animate-pulse" />
                Redirecting to intelligence report...
              </p>
            )}

            {projectName && (
              <p className="text-yowon-muted text-sm mt-2">
                Evaluating{' '}
                <span className="text-cyan-300 font-semibold">{projectName}</span>
                {projectType && (
                  <span className="ml-2 status-badge info text-[10px]">{projectType}</span>
                )}
              </p>
            )}
          </div>

          {/* Stats strip */}
          <div className="grid grid-cols-3 gap-3 mb-5 max-w-lg mx-auto">
            {SIMULATION_STATS.map(({ label, value, icon: Icon, tone }) => (
              <motion.div
                key={label}
                className="metric-card !py-3 text-center"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Icon size={16} className={`mx-auto mb-1.5 ${tone}`} />
                <p className={`text-sm font-bold ${tone}`}>{value}</p>
                <p className="mc-label mt-0.5">{label}</p>
              </motion.div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="max-w-lg mx-auto">
            <div className="flex justify-between text-[11px] font-mono text-yowon-muted mb-2">
              <span className="flex items-center gap-1.5">
                <Clock size={11} />
                {formatTime(elapsed)}
              </span>
              <span className="text-cyan-300 font-semibold">{completionPct}%</span>
            </div>
            <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-300 via-emerald-300 to-violet-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${completionPct}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
            {progress.current_task && (
              <p className="text-[11px] text-yowon-muted mt-2 text-center truncate">
                {progress.current_task}
              </p>
            )}
          </div>
        </motion.div>

        {/* ---- Main grid ---- */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* Pipeline sidebar */}
          <div className="xl:col-span-1">
            <p className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em] mb-3">
              Evaluation Pipeline
            </p>
            <div className="space-y-1">
              {visiblePipeline.map((agent, i) => (
                <AgentPipelineCard
                  key={agent.id}
                  label={agent.label}
                  description={agent.desc}
                  status={agentStatuses[i]}
                  index={i}
                  icon={agent.icon}
                  color={agent.color}
                />
              ))}
            </div>
          </div>

          {/* Main content */}
          <div className="xl:col-span-2 space-y-5">

            {/* Agent network */}
            <div className="cyber-glow-card">
              <div className="cyber-glow-inner !p-5">
                <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/[0.03] to-transparent pointer-events-none rounded-[inherit]" />
                <p className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em] mb-4 text-center">
                  Judge Simulation Network
                </p>
                <AgentNetwork
                  activeAgent={activeAgent}
                  agentStates={progress.agent_states}
                  statuses={agentStatuses}
                  showPresentation={isPresentationEnabled(projectType)}
                />
              </div>
            </div>

            {/* Timeline + Terminal */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <EvaluationTimeline events={progress.events} elapsedSeconds={elapsed} />
              <TerminalLog logs={progress.logs} />
            </div>
          </div>
        </div>

        {/* ---- Error states ---- */}
        <AnimatePresence>
          {isDone && reportStatus === 'failed' && (
            <motion.div
              className="mt-8 glass-card !p-6 text-center accent-amber"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <p className="text-amber-300 font-semibold mb-1">Report Generation Failed</p>
              <p className="text-yowon-muted text-xs mb-4 font-mono">
                {reportError || 'PDF could not be built. JSON verdict is still available.'}
              </p>
              <button
                onClick={() => navigate(`/report/${projectId}`)}
                className="yowon-btn-primary yowon-btn-sm"
              >
                View Verdict Report <ChevronRight size={14} />
              </button>
            </motion.div>
          )}

          {isFailed && (
            <motion.div
              className="mt-8 glass-card !p-6 text-center accent-red"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            >
              <XCircle className="mx-auto mb-3 text-red-400" size={32} />
              <p className="text-red-400 text-sm mb-4">
                Evaluation pipeline failed. Ensure Ollama is running with qwen2.5:3b and qwen3:8b pulled.
              </p>
              <button onClick={() => navigate('/submit')} className="yowon-btn-primary yowon-btn-sm">
                Try Again
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <p className="text-center text-[10px] text-yowon-muted mt-8 font-mono">
          Target: &lt;60s evaluation · Real-time SSE progress · No simulated updates
        </p>
      </main>
    </AppShell>
  )
}

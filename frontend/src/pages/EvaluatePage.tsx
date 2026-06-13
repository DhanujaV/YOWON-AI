import { useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Clock, CheckCircle, XCircle, Brain, Cpu, Shield, Presentation,
  Lightbulb, Globe, Gavel, Activity, Scale, Fingerprint, Trophy,
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
  { id: 'coordinator', label: 'Coordinator', desc: 'Parsing inputs and building evaluation context', icon: Brain, color: '#00E5FF' },
  { id: 'technical', label: 'Forge', desc: 'Analyzing architecture and code quality', icon: Cpu, color: '#00E5FF' },
  { id: 'security', label: 'Sentinel', desc: 'Auditing OWASP risks and static scan findings', icon: Shield, color: '#EF4444' },
  { id: 'presentation', label: 'Showcase', desc: 'Reviewing pitch deck and documentation', icon: Presentation, color: '#7C3AED' },
  { id: 'innovation', label: 'Visionary', desc: 'Assessing novelty and scalability readiness', icon: Lightbulb, color: '#00FFA3' },
  { id: 'risk', label: 'Guardian', desc: 'Forecasting impact and failure modes', icon: Globe, color: '#00FFA3' },
  { id: 'chief', label: 'YOWON Prime', desc: 'Cross-examining the Council and rendering verdict', icon: Gavel, color: '#7C3AED' },
]

function isPresentationEnabled(projectType?: string) {
  return projectType === 'Hackathon Project'
}

const SIMULATION_STATS = [
  { label: 'Judge Simulation', value: 'Active', icon: Scale, tone: 'text-cyan-300' },
  { label: 'Project DNA', value: 'Mapping', icon: Fingerprint, tone: 'text-emerald-300' },
  { label: 'Global Rank', value: 'Pending', icon: Trophy, tone: 'text-violet-300' },
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
  if (state?.status === 'failed') return 'failed'
  if (state?.status === 'running') return 'running'
  if (globalStatus === 'done') return 'completed'
  const normalizedActive = activeAgent === 'brief' ? 'coordinator' : activeAgent
  const idx = pipeline.findIndex(p => p.id === agentId)
  const activeIdx = pipeline.findIndex(p => p.id === normalizedActive)
  if (activeIdx < 0) return 'waiting'
  if (idx < activeIdx) return 'completed'
  if (idx === activeIdx) return 'running'
  return 'waiting'
}

export default function EvaluatePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const onComplete = useCallback(
    (id: string) => setTimeout(() => navigate(`/report/${id}`), 1400),
    [navigate],
  )

  const { status, reportStatus, reportError, projectName, projectType, progress } =
    useEvaluationProgress(projectId, onComplete)

  const activeAgent = progress.agent === 'brief' ? 'coordinator' : progress.agent
  const elapsed = progress.elapsed_seconds ?? 0
  const completionPct = progress.completion_percent ?? 0
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
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <AppShell particles={false}>
      <NeuralOverlay />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <motion.div
          className="text-center mb-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {status === 'done' ? (
            <CheckCircle size={48} className="mx-auto mb-4 text-emerald-400" />
          ) : status === 'failed' ? (
            <XCircle size={48} className="mx-auto mb-4 text-red-400" />
          ) : (
            <motion.div
              className="relative w-20 h-20 mx-auto mb-4"
              animate={{ boxShadow: ['0 0 20px rgba(0,229,255,0.2)', '0 0 50px rgba(0,255,163,0.34)', '0 0 20px rgba(0,229,255,0.2)'] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <div className="absolute inset-0 rounded-full border-2 border-cyan-300/30" />
              <div className="absolute inset-0 rounded-full border-2 border-t-cyan-300 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
              <Brain size={28} className="absolute inset-0 m-auto text-cyan-300" />
            </motion.div>
          )}

          <p className="text-xs font-mono text-cyan-300/80 uppercase tracking-[0.3em] mb-2">
            Mission Control
          </p>
          <h1 className="text-2xl sm:text-4xl font-display font-bold mb-2">
            {status === 'failed' ? 'Evaluation Failed' :
             status === 'done' ? 'Evaluation Complete' :
             'AI Jury Deliberation In Progress'}
          </h1>
          {status === 'done' && reportStatus === 'failed' && (
            <p className="text-amber-400/90 text-sm mt-2 max-w-lg mx-auto">
              Verdict ready. PDF report generation failed. View results below.
            </p>
          )}
          {status === 'done' && reportStatus === 'ready' && (
            <p className="text-emerald-400/80 text-sm mt-2">Redirecting to intelligence report...</p>
          )}

          {projectName && (
            <p className="text-yowon-muted">
              Evaluating <span className="text-cyan-300 font-medium">{projectName}</span>
              {projectType && <span className="text-emerald-300 font-mono text-xs"> - {projectType}</span>}
            </p>
          )}

          <div className="flex flex-wrap items-center justify-center gap-4 mt-5 text-sm font-mono">
            <span className="flex items-center gap-1.5 text-yowon-muted glass-pill px-3 py-1.5">
              <Clock size={14} />
              {formatTime(elapsed)}
            </span>
            <span className="flex items-center gap-1.5 text-cyan-300/90 glass-pill px-3 py-1.5">
              <Activity size={14} />
              {completionPct}% complete
            </span>
            <span className="text-emerald-300/80 glass-pill px-3 py-1.5 text-xs">
              {progress.current_task ?? 'Initializing...'}
            </span>
          </div>

          <div className="mt-4 max-w-md mx-auto">
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-300 via-emerald-300 to-violet-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${completionPct}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {SIMULATION_STATS.map(({ label, value, icon: Icon, tone }) => (
            <motion.div
              key={label}
              className="glass-card p-4 flex items-center justify-between"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div>
                <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">{label}</p>
                <p className={`text-lg font-display font-semibold ${tone}`}>{value}</p>
              </div>
              <Icon className={tone} size={24} />
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-1 space-y-1">
            <h2 className="text-xs font-mono text-yowon-muted uppercase tracking-[0.2em] mb-4 px-1">
              Evaluation Pipeline
            </h2>
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

          <div className="xl:col-span-2 space-y-6">
            <div className="glass-card p-6 border border-cyan-300/10">
              <h2 className="text-xs font-mono text-yowon-muted uppercase tracking-[0.2em] mb-4 text-center">
                Judge Simulation Network
              </h2>
              <AgentNetwork
                activeAgent={activeAgent}
                agentStates={progress.agent_states}
                statuses={agentStatuses}
                showPresentation={isPresentationEnabled(projectType)}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <EvaluationTimeline
                events={progress.events}
                elapsedSeconds={elapsed}
              />
              <TerminalLog logs={progress.logs} />
            </div>
          </div>
        </div>

        {status === 'done' && reportStatus === 'failed' && (
          <motion.div
            className="mt-8 glass-card p-6 text-center border border-amber-500/25"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <p className="text-amber-300 text-sm mb-2 font-display font-semibold">
              Report Generation Failed
            </p>
            <p className="text-yowon-muted text-xs mb-4 font-mono">
              {reportError || 'PDF could not be built. JSON verdict is still available.'}
            </p>
            <button
              onClick={() => navigate(`/report/${projectId}`)}
              className="yowon-btn-primary text-sm py-2 px-6"
            >
              View Verdict Report
            </button>
          </motion.div>
        )}

        {status === 'failed' && (
          <motion.div
            className="mt-8 glass-card p-6 text-center border border-red-500/20"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <p className="text-red-400 text-sm mb-4">
              Evaluation pipeline failed. Ensure Ollama is running with qwen2.5:3b and qwen3:8b pulled.
            </p>
            <button onClick={() => navigate('/submit')} className="yowon-btn-primary text-sm py-2 px-6">
              Try Again
            </button>
          </motion.div>
        )}

        <p className="text-center text-xs text-yowon-muted mt-8 font-mono">
          Target: &lt;60s evaluation - Real-time SSE progress - No simulated updates
        </p>
      </main>
    </AppShell>
  )
}

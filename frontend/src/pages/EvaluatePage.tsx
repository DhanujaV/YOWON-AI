import { useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Clock, CheckCircle, XCircle, Brain, Cpu, Shield, Presentation,
  Lightbulb, Globe, Gavel, Activity,
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
  { id: 'coordinator', label: 'Coordinator', desc: 'Parsing inputs and building evaluation context', icon: Brain, color: '#818CF8' },
  { id: 'technical', label: 'Engineering Agent', desc: 'Analyzing architecture and code quality', icon: Cpu, color: '#A855F7' },
  { id: 'security', label: 'Security Agent', desc: 'Auditing OWASP risks and static scan findings', icon: Shield, color: '#EF4444' },
  { id: 'presentation', label: 'Presentation Agent', desc: 'Reviewing pitch deck and documentation', icon: Presentation, color: '#A78BFA' },
  { id: 'innovation', label: 'Innovation Agent', desc: 'Assessing novelty and scalability readiness', icon: Lightbulb, color: '#F59E0B' },
  { id: 'risk', label: 'Risk Agent', desc: 'Forecasting impact and failure modes', icon: Globe, color: '#10B981' },
  { id: 'chief', label: 'Chief Evaluator', desc: 'Cross-examining specialists and rendering verdict', icon: Gavel, color: '#14B8A6' },
]

function resolveAgentStatus(
  agentId: string,
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
  const idx = PIPELINE.findIndex(p => p.id === agentId)
  const activeIdx = PIPELINE.findIndex(p => p.id === normalizedActive)
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

  const agentStatuses = useMemo<AgentStatus[]>(() => {
    return PIPELINE.map(p =>
      resolveAgentStatus(p.id, progress.agent_states, activeAgent, status),
    )
  }, [progress.agent_states, activeAgent, status])

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
              animate={{ boxShadow: ['0 0 20px rgba(6,182,212,0.2)', '0 0 50px rgba(6,182,212,0.4)', '0 0 20px rgba(6,182,212,0.2)'] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <div className="absolute inset-0 rounded-full border-2 border-violet-500/30" />
              <div className="absolute inset-0 rounded-full border-2 border-t-violet-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" />
              <Brain size={28} className="absolute inset-0 m-auto text-violet-300" />
            </motion.div>
          )}

          <p className="text-xs font-mono text-pink-400/70 uppercase tracking-[0.3em] mb-2">
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
              Evaluating <span className="text-violet-300 font-medium">{projectName}</span>
              {projectType && <span className="text-pink-300 font-mono text-xs"> - {projectType}</span>}
            </p>
          )}

          <div className="flex flex-wrap items-center justify-center gap-4 mt-5 text-sm font-mono">
            <span className="flex items-center gap-1.5 text-yowon-muted glass-pill px-3 py-1.5">
              <Clock size={14} />
              {formatTime(elapsed)}
            </span>
            <span className="flex items-center gap-1.5 text-pink-400/90 glass-pill px-3 py-1.5">
              <Activity size={14} />
              {completionPct}% complete
            </span>
            <span className="text-purple-300/80 glass-pill px-3 py-1.5 text-xs">
              {progress.current_task ?? 'Initializing...'}
            </span>
          </div>

          <div className="mt-4 max-w-md mx-auto">
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-violet-500 via-pink-500 to-amber-400 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${completionPct}%` }}
                transition={{ duration: 0.4 }}
              />
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-1 space-y-1">
            <h2 className="text-xs font-mono text-yowon-muted uppercase tracking-[0.2em] mb-4 px-1">
              Evaluation Pipeline
            </h2>
            {PIPELINE.map((agent, i) => (
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
            <div className="glass-card p-6 border border-violet-500/10">
              <h2 className="text-xs font-mono text-yowon-muted uppercase tracking-[0.2em] mb-4 text-center">
                AI Agent Network
              </h2>
              <AgentNetwork
                activeAgent={activeAgent}
                agentStates={progress.agent_states}
                statuses={agentStatuses}
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

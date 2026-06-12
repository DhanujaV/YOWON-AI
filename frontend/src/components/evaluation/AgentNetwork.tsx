import { memo, useCallback, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Background,
  BaseEdge,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
  getBezierPath,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Cpu, Shield, Presentation, Lightbulb, Globe, Gavel, Brain,
  Expand, X, Activity, CheckCircle, Clock,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { AgentStateEntry, AgentStatus } from '../../types'

const AGENT_WIDTH = 156
const AGENT_HEIGHT = 72

const AGENTS = [
  {
    id: 'coordinator',
    icon: Brain,
    label: 'Coordinator',
    role: 'Evaluation Orchestrator',
    color: '#00E5FF',
    position: { x: 322, y: 38 },
  },
  {
    id: 'technical',
    icon: Cpu,
    label: 'Engineering Agent',
    role: 'Architecture Analysis',
    color: '#00E5FF',
    position: { x: 36, y: 176 },
  },
  {
    id: 'security',
    icon: Shield,
    label: 'Security Agent',
    role: 'Security Review',
    color: '#EF4444',
    position: { x: 232, y: 206 },
  },
  {
    id: 'presentation',
    icon: Presentation,
    label: 'Presentation Agent',
    role: 'Pitch Evaluation',
    color: '#7C3AED',
    position: { x: 428, y: 206 },
  },
  {
    id: 'innovation',
    icon: Lightbulb,
    label: 'Innovation Agent',
    role: 'Novelty Analysis',
    color: '#00FFA3',
    position: { x: 624, y: 176 },
  },
  {
    id: 'risk',
    icon: Globe,
    label: 'Risk Agent',
    role: 'Risk Assessment',
    color: '#00FFA3',
    position: { x: 146, y: 356 },
  },
  {
    id: 'chief',
    icon: Gavel,
    label: 'Chief Evaluator',
    role: 'Verdict Synthesis',
    color: '#7C3AED',
    position: { x: 516, y: 356 },
  },
] as const

const RELATIONSHIPS = [
  ['coordinator', 'technical'],
  ['coordinator', 'security'],
  ['coordinator', 'presentation'],
  ['coordinator', 'innovation'],
  ['coordinator', 'risk'],
  ['technical', 'chief'],
  ['security', 'chief'],
  ['presentation', 'chief'],
  ['innovation', 'chief'],
  ['risk', 'chief'],
] as const

const STATUS_LABEL: Record<AgentStatus, string> = {
  waiting: 'Waiting',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
}

interface AgentDetail {
  id: string
  icon: LucideIcon
  label: string
  role: string
  color: string
  position: { x: number; y: number }
  status: AgentStatus
  score?: number
  confidence?: number
  state?: AgentStateEntry
}

interface AgentNodeData extends Record<string, unknown> {
  agent: AgentDetail
  active: boolean
  networkHovered: boolean
  onSelect: (agentId: string) => void
}

type AgentFlowNode = Node<AgentNodeData, 'agent'>

interface AgentNetworkProps {
  activeAgent: string
  agentStates?: Record<string, AgentStateEntry>
  statuses: AgentStatus[]
}

function nodeStatus(
  id: string,
  agentStates?: Record<string, AgentStateEntry>,
  statuses?: AgentStatus[],
  index?: number,
): AgentStatus {
  const state = agentStates?.[id]
  if (state?.status === 'failed') return 'failed'
  if (state?.status === 'completed') return 'completed'
  if (state?.status === 'running') return 'running'
  return statuses?.[index ?? 0] ?? 'waiting'
}

function statusClasses(status: AgentStatus) {
  if (status === 'completed') {
    return {
      shell: 'border-emerald-300/55 bg-emerald-400/[0.10] shadow-[0_0_30px_rgba(0,255,163,0.24)]',
      dot: 'bg-emerald-300 shadow-[0_0_12px_rgba(0,255,163,0.9)]',
      text: 'text-emerald-200',
    }
  }

  if (status === 'running') {
    return {
      shell: 'border-cyan-300/70 bg-cyan-300/[0.12] shadow-[0_0_36px_rgba(0,229,255,0.34)]',
      dot: 'bg-cyan-300 shadow-[0_0_14px_rgba(0,229,255,0.9)]',
      text: 'text-cyan-200',
    }
  }

  if (status === 'failed') {
    return {
      shell: 'border-red-300/60 bg-red-500/[0.12] shadow-[0_0_28px_rgba(239,68,68,0.24)]',
      dot: 'bg-red-300 shadow-[0_0_12px_rgba(239,68,68,0.9)]',
      text: 'text-red-200',
    }
  }

  return {
    shell: 'border-white/10 bg-white/[0.035] opacity-60',
    dot: 'bg-slate-500',
    text: 'text-slate-400',
  }
}

function formatMetric(value?: number, suffix = '') {
  if (value === undefined || value === null || Number.isNaN(value)) return 'Pending'
  return `${Math.round(value)}${suffix}`
}

function fallbackList(agent: AgentDetail, kind: 'strengths' | 'weaknesses' | 'risks' | 'evidence' | 'files') {
  if (agent.status === 'failed' && kind === 'risks') {
    return [agent.state?.error ?? 'Agent reported a failed execution state.']
  }

  if (kind === 'strengths') return ['Awaiting final evaluation evidence.']
  if (kind === 'weaknesses') return ['Awaiting final evaluation evidence.']
  if (kind === 'risks') return ['No live risk details available in progress state.']
  if (kind === 'evidence') return ['Evidence appears in the completed verdict report.']
  return ['File-level details appear in the completed verdict report.']
}

const AgentNode = memo(function AgentNode({ data }: NodeProps<AgentFlowNode>) {
  const { agent, active, networkHovered, onSelect } = data
  const Icon = agent.icon as LucideIcon
  const classes = statusClasses(agent.status)
  const glowing = networkHovered && agent.status !== 'waiting'

  return (
    <button
      type="button"
      onClick={() => onSelect(agent.id)}
      className="group relative block w-[156px] cursor-pointer rounded-[8px] text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/80"
      aria-label={`Open ${agent.label} details`}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-cyan-200/60 !bg-cyan-300/80" />
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-cyan-200/60 !bg-cyan-300/80" />

      {agent.status === 'running' && (
        <motion.div
          className="absolute -inset-2 rounded-[10px] border border-t-cyan-200/80 border-r-transparent border-b-violet-300/50 border-l-transparent"
          animate={{ rotate: 360 }}
          transition={{ duration: 3.2, repeat: Infinity, ease: 'linear' }}
        />
      )}

      <motion.div
        className={`relative h-[72px] overflow-visible rounded-[8px] border px-3 py-3 backdrop-blur-xl transition-all duration-300 ${classes.shell}`}
        animate={{
          scale: active ? [1, 1.035, 1] : glowing ? 1.025 : 1,
          boxShadow: glowing
            ? `0 0 34px ${agent.color}55, inset 0 0 22px ${agent.color}18`
            : undefined,
        }}
        transition={{ duration: active ? 1.6 : 0.25, repeat: active ? Infinity : 0 }}
      >
        <div className="absolute inset-0 rounded-[8px] bg-[radial-gradient(circle_at_20%_0%,rgba(255,255,255,0.14),transparent_34%),linear-gradient(135deg,rgba(0,229,255,0.08),rgba(124,58,237,0.08))]" />
        <div className="relative flex items-center gap-3">
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[8px] border border-white/10 bg-slate-950/70"
            style={{ boxShadow: active || glowing ? `0 0 20px ${agent.color}66` : undefined }}
          >
            <Icon size={18} style={{ color: agent.status === 'waiting' ? '#64748B' : agent.color }} />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[12px] font-display font-semibold text-yowon-text">{agent.label}</p>
            <p className="truncate text-[9px] font-mono uppercase tracking-widest text-yowon-muted">{agent.role}</p>
            <div className="mt-1 flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${classes.dot}`} />
              <span className={`text-[9px] font-mono uppercase ${classes.text}`}>{STATUS_LABEL[agent.status]}</span>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="pointer-events-none absolute left-1/2 top-[-118px] z-40 hidden w-[220px] -translate-x-1/2 rounded-[8px] border border-cyan-200/20 bg-[#07111F]/95 p-3 shadow-[0_20px_60px_rgba(0,0,0,0.45)] backdrop-blur-xl group-hover:block">
        <p className="text-xs font-display font-semibold text-cyan-100">{agent.label}</p>
        <p className="mt-1 text-[10px] font-mono text-yowon-muted">Role: <span className="text-yowon-text">{agent.role}</span></p>
        <p className="text-[10px] font-mono text-yowon-muted">Status: <span className={classes.text}>{STATUS_LABEL[agent.status]}</span></p>
        <p className="text-[10px] font-mono text-yowon-muted">Score: <span className="text-emerald-200">{formatMetric(agent.score)}</span></p>
        <p className="text-[10px] font-mono text-yowon-muted">Confidence: <span className="text-cyan-200">{formatMetric(agent.confidence, '%')}</span></p>
      </div>
    </button>
  )
})

function AnimatedEdge(props: EdgeProps) {
  const [edgePath] = getBezierPath(props)
  const active = props.data?.active === true

  return (
    <g>
      <BaseEdge
        path={edgePath}
        markerEnd={props.markerEnd}
        style={{
          stroke: active ? 'rgba(0,229,255,0.62)' : 'rgba(125,211,252,0.22)',
          strokeWidth: active ? 2.2 : 1.3,
          filter: active ? 'drop-shadow(0 0 9px rgba(0,229,255,0.75))' : undefined,
        }}
      />
      <path
        d={edgePath}
        fill="none"
        stroke={active ? 'rgba(0,255,255,0.28)' : 'rgba(124,58,237,0.18)'}
        strokeDasharray="6 12"
        strokeWidth={active ? 1.8 : 1}
      >
        <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1.2s" repeatCount="indefinite" />
      </path>
      {active && [0, 0.35, 0.7].map((offset) => (
        <circle key={offset} r="3.5" fill="#67E8F9" style={{ filter: 'drop-shadow(0 0 8px #22D3EE)' }}>
          <animateMotion path={edgePath} dur="1.8s" begin={`${offset}s`} repeatCount="indefinite" />
        </circle>
      ))}
    </g>
  )
}

const edgeTypes = { animatedSignal: AnimatedEdge }
const nodeTypes = { agent: AgentNode }

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-[8px] border border-white/10 bg-white/[0.035] p-3">
      <p className="mb-2 text-[10px] font-mono uppercase tracking-widest text-cyan-200">{title}</p>
      <div className="space-y-1.5">
        {items.map(item => (
          <p key={item} className="text-xs leading-relaxed text-yowon-muted">{item}</p>
        ))}
      </div>
    </div>
  )
}

function AgentDetailModal({ agent, onClose }: { agent: AgentDetail; onClose: () => void }) {
  const classes = statusClasses(agent.status)
  const Icon = agent.icon as LucideIcon

  return (
    <motion.div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className="w-full max-w-3xl overflow-hidden rounded-[8px] border border-cyan-200/20 bg-[#07111F]/95 shadow-[0_0_80px_rgba(0,229,255,0.18)]"
        initial={{ scale: 0.96, y: 18 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.97, y: 10 }}
        onClick={event => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-white/10 bg-gradient-to-r from-cyan-300/[0.09] via-violet-500/[0.08] to-transparent p-5">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-[8px] border border-white/10 bg-slate-950/70" style={{ boxShadow: `0 0 24px ${agent.color}55` }}>
              <Icon size={22} style={{ color: agent.color }} />
            </div>
            <div>
              <p className="font-display text-xl font-bold text-yowon-text">{agent.label}</p>
              <p className="text-xs font-mono uppercase tracking-widest text-yowon-muted">{agent.role}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-[8px] border border-white/10 text-yowon-muted transition hover:border-cyan-200/40 hover:text-cyan-100"
            aria-label="Close agent details"
          >
            <X size={18} />
          </button>
        </div>

        <div className="grid gap-3 p-5 sm:grid-cols-4">
          <div className="rounded-[8px] border border-white/10 bg-white/[0.035] p-3">
            <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Status</p>
            <p className={`mt-2 font-display text-lg font-semibold ${classes.text}`}>{STATUS_LABEL[agent.status]}</p>
          </div>
          <div className="rounded-[8px] border border-white/10 bg-white/[0.035] p-3">
            <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Score</p>
            <p className="mt-2 font-display text-lg font-semibold text-emerald-200">{formatMetric(agent.score)}</p>
          </div>
          <div className="rounded-[8px] border border-white/10 bg-white/[0.035] p-3">
            <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Confidence</p>
            <p className="mt-2 font-display text-lg font-semibold text-cyan-200">{formatMetric(agent.confidence, '%')}</p>
          </div>
          <div className="rounded-[8px] border border-white/10 bg-white/[0.035] p-3">
            <p className="text-[10px] font-mono uppercase tracking-widest text-yowon-muted">Runtime</p>
            <p className="mt-2 font-display text-lg font-semibold text-violet-200">
              {agent.state?.duration_sec != null ? `${agent.state.duration_sec}s` : 'Pending'}
            </p>
          </div>
        </div>

        <div className="grid gap-3 px-5 pb-5 md:grid-cols-2">
          <DetailList title="Strengths" items={fallbackList(agent, 'strengths')} />
          <DetailList title="Weaknesses" items={fallbackList(agent, 'weaknesses')} />
          <DetailList title="Risks" items={fallbackList(agent, 'risks')} />
          <DetailList title="Evidence Detected" items={fallbackList(agent, 'evidence')} />
          <div className="md:col-span-2">
            <DetailList title="Files Analyzed" items={fallbackList(agent, 'files')} />
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

function NetworkCanvas({
  agents,
  activeAgent,
  networkHovered,
  fullscreen = false,
  onSelect,
}: {
  agents: AgentDetail[]
  activeAgent: string
  networkHovered: boolean
  fullscreen?: boolean
  onSelect: (agentId: string) => void
}) {
  const nodes = useMemo<AgentFlowNode[]>(() => agents.map(agent => ({
    id: agent.id,
    type: 'agent',
    position: agent.position,
    data: {
      agent,
      active: activeAgent === agent.id || (activeAgent === 'brief' && agent.id === 'coordinator'),
      networkHovered,
      onSelect,
    },
    draggable: true,
    style: { width: AGENT_WIDTH, height: AGENT_HEIGHT },
  })), [activeAgent, agents, networkHovered, onSelect])

  const edges = useMemo<Edge[]>(() => RELATIONSHIPS.map(([source, target]) => {
    const sourceAgent = agents.find(agent => agent.id === source)
    const targetAgent = agents.find(agent => agent.id === target)
    const active = sourceAgent?.status === 'running'
      || sourceAgent?.status === 'completed'
      || targetAgent?.status === 'running'
      || networkHovered

    return {
      id: `${source}-${target}`,
      source,
      target,
      type: 'animatedSignal',
      data: { active },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: active ? '#67E8F9' : 'rgba(125,211,252,0.28)',
      },
    }
  }), [agents, networkHovered])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      fitView
      fitViewOptions={{ padding: fullscreen ? 0.18 : 0.12 }}
      minZoom={0.35}
      maxZoom={1.8}
      nodesDraggable
      panOnDrag
      zoomOnScroll
      zoomOnPinch
      zoomOnDoubleClick
      proOptions={{ hideAttribution: true }}
      className="agent-network-flow"
    >
      <Background color="rgba(103,232,249,0.18)" gap={28} size={1} />
      <Controls
        position="bottom-right"
        showInteractive={false}
        className="!rounded-[8px] !border !border-cyan-200/20 !bg-slate-950/80 !shadow-[0_0_24px_rgba(0,229,255,0.14)] [&_button]:!border-cyan-200/10 [&_button]:!bg-transparent [&_button]:!text-cyan-100"
      />
    </ReactFlow>
  )
}

export default function AgentNetwork({ activeAgent, agentStates, statuses }: AgentNetworkProps) {
  const [networkHovered, setNetworkHovered] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [fullscreen, setFullscreen] = useState(false)

  const agents = useMemo<AgentDetail[]>(() => AGENTS.map((agent, index) => ({
    ...agent,
    status: nodeStatus(agent.id, agentStates, statuses, index),
    state: agentStates?.[agent.id],
  })), [agentStates, statuses])

  const selectedAgent = useMemo(
    () => agents.find(agent => agent.id === selectedAgentId),
    [agents, selectedAgentId],
  )

  const runningCount = agents.filter(agent => agent.status === 'running').length
  const completedCount = agents.filter(agent => agent.status === 'completed').length

  const handleSelect = useCallback((agentId: string) => {
    setSelectedAgentId(agentId)
  }, [])

  return (
    <>
      <motion.div
        className="relative mx-auto h-[430px] w-full max-w-[860px] overflow-hidden rounded-[8px] border border-cyan-200/10 bg-[#06101D] shadow-[inset_0_0_80px_rgba(0,229,255,0.06)]"
        onHoverStart={() => setNetworkHovered(true)}
        onHoverEnd={() => setNetworkHovered(false)}
        animate={{ scale: networkHovered ? 1.015 : 1 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,rgba(0,229,255,0.16),transparent_32%),radial-gradient(circle_at_76%_72%,rgba(124,58,237,0.16),transparent_28%)]" />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:42px_42px]" />

        <div className="absolute left-4 top-4 z-10 flex items-center gap-2 rounded-[8px] border border-cyan-200/15 bg-slate-950/60 px-3 py-2 backdrop-blur-xl">
          <Activity size={14} className="text-cyan-300" />
          <span className="text-[10px] font-mono uppercase tracking-widest text-cyan-100">Agent Mesh</span>
        </div>

        <div className="absolute bottom-4 left-4 z-10 flex flex-wrap gap-2">
          <span className="flex items-center gap-1.5 rounded-[8px] border border-cyan-200/15 bg-slate-950/60 px-2.5 py-1.5 text-[10px] font-mono text-cyan-100 backdrop-blur-xl">
            <Clock size={12} /> {runningCount} running
          </span>
          <span className="flex items-center gap-1.5 rounded-[8px] border border-emerald-200/15 bg-slate-950/60 px-2.5 py-1.5 text-[10px] font-mono text-emerald-100 backdrop-blur-xl">
            <CheckCircle size={12} /> {completedCount} completed
          </span>
        </div>

        <button
          type="button"
          onClick={() => setFullscreen(true)}
          className="absolute right-4 top-4 z-20 flex h-10 w-10 items-center justify-center rounded-[8px] border border-cyan-200/20 bg-slate-950/70 text-cyan-100 backdrop-blur-xl transition hover:border-cyan-200/50 hover:bg-cyan-300/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
          aria-label="Open fullscreen network"
        >
          <Expand size={17} />
        </button>

        <NetworkCanvas
          agents={agents}
          activeAgent={activeAgent}
          networkHovered={networkHovered}
          onSelect={handleSelect}
        />
      </motion.div>

      <AnimatePresence>
        {fullscreen && (
          <motion.div
            className="fixed inset-0 z-[60] bg-[#030914]/95 p-4 backdrop-blur-xl"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="relative h-full overflow-hidden rounded-[8px] border border-cyan-200/20 bg-[#06101D]">
              <div className="absolute left-4 top-4 z-20 rounded-[8px] border border-cyan-200/15 bg-slate-950/70 px-4 py-3 backdrop-blur-xl">
                <p className="text-xs font-mono uppercase tracking-[0.28em] text-cyan-200">Judge Simulation Network</p>
                <p className="mt-1 text-sm text-yowon-muted">Mission-control view with pan, zoom, and draggable agents.</p>
              </div>
              <button
                type="button"
                onClick={() => setFullscreen(false)}
                className="absolute right-4 top-4 z-20 flex h-11 w-11 items-center justify-center rounded-[8px] border border-cyan-200/20 bg-slate-950/75 text-cyan-100 backdrop-blur-xl transition hover:border-cyan-200/50 hover:bg-cyan-300/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
                aria-label="Close fullscreen network"
              >
                <X size={19} />
              </button>
              <NetworkCanvas
                agents={agents}
                activeAgent={activeAgent}
                networkHovered
                fullscreen
                onSelect={handleSelect}
              />
            </div>
          </motion.div>
        )}

        {selectedAgent && (
          <AgentDetailModal agent={selectedAgent} onClose={() => setSelectedAgentId(null)} />
        )}
      </AnimatePresence>
    </>
  )
}

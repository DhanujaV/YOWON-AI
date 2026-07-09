import React from 'react'
import { Cpu, Wrench, MessageSquare, Database, List, ShieldAlert } from 'lucide-react'
import { useAIIntelligence } from './queries'
import { CardSkeleton } from './Skeletons'
import { ErrorBoundary } from './ErrorBoundary'

interface AIAgentsPanelProps {
  projectId: string
}

export function AIAgentsPanel({ projectId }: AIAgentsPanelProps) {
  return (
    <ErrorBoundary name="AI Agents Panel">
      <AIAgentsContent projectId={projectId} />
    </ErrorBoundary>
  )
}

function AIAgentsContent({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useAIIntelligence(projectId)

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3].map(i => <CardSkeleton key={i} />)}
      </div>
    )
  }

  if (error || !data || !data.success) {
    return (
      <div className="glass-card flex items-center gap-3 text-rose-300 p-5 font-mono">
        <ShieldAlert size={20} />
        <span>Failed to load AI agent telemetry. Ensure AI frameworks (CrewAI, LangChain) are configured.</span>
      </div>
    )
  }

  const ai = data.data
  const agents = ai.agents || []
  const tools = ai.tools || []
  const llms = ai.llms || []
  const prompts = ai.prompts || []
  const comm = ai.communication || []

  return (
    <div className="space-y-6">
      {/* Framework Summary */}
      <div className="glass-card bg-gradient-to-r from-violet-950/20 via-cyan-950/20 to-violet-950/30 border border-violet-500/20 p-5 rounded-xl flex items-center justify-between">
        <div className="space-y-1">
          <span className="text-[10px] font-mono text-cyan-300 uppercase tracking-widest block">AI Framework Detected</span>
          <h3 className="text-xl font-display font-bold text-yowon-text">{ai.framework || 'None'}</h3>
        </div>
        <div className="bg-white/5 border border-white/10 px-4 py-2 rounded-lg text-xs font-mono text-cyan-300">
          Orchestration: {ai.orchestration}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agent topology map list */}
        <div className="lg:col-span-2 glass-card space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h4 className="font-display font-bold text-lg text-yowon-text flex items-center gap-2">
              <Cpu size={18} className="text-violet-300" /> Agent Team Topology
            </h4>
            <span className="text-xs font-mono bg-violet-500/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded-full">
              {agents.length} Active
            </span>
          </div>

          <div className="space-y-3">
            {agents.map((agent: string, i: number) => (
              <div key={i} className="bg-white/5 border border-white/10 rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 group hover:border-violet-500/30 transition-colors">
                <div className="space-y-1">
                  <h5 className="font-display font-bold text-sm text-yowon-text group-hover:text-violet-300 transition-colors">{agent}</h5>
                  <p className="text-xs text-yowon-muted font-sans">
                    System role mapping coordinates execution tasks dynamically.
                  </p>
                </div>
                <div className="flex gap-2">
                  <span className="text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 px-2 py-0.5 rounded">
                    ReAct Planner
                  </span>
                  <span className="text-[10px] font-mono bg-violet-500/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded">
                    Tool Access
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Comm Graph representation */}
          {comm.length > 0 && (
            <div className="pt-4 border-t border-white/5">
              <h5 className="text-xs font-mono text-cyan-300 uppercase tracking-wider mb-3">Communication Flows</h5>
              <div className="space-y-2">
                {comm.map((c: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-xs font-mono text-yowon-muted">
                    <span className="text-yowon-text">{c.source}</span>
                    <span className="text-violet-400">─{c.label}─▶</span>
                    <span className="text-yowon-text">{c.target}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar details */}
        <div className="space-y-6">
          {/* Agent tools list */}
          <div className="glass-card space-y-4">
            <h4 className="font-display font-bold text-sm text-yowon-text flex items-center gap-2 border-b border-white/5 pb-2">
              <List size={16} className="text-cyan-300" /> Custom Agent Tools
            </h4>
            <div className="flex flex-wrap gap-1.5">
              {tools.map((tool: string, i: number) => (
                <span key={i} className="text-[10px] font-mono bg-white/5 text-cyan-300 border border-white/10 hover:border-cyan-500/30 px-2.5 py-1 rounded transition-colors">
                  {tool}
                </span>
              ))}
              {tools.length === 0 && (
                <span className="text-xs italic text-yowon-muted font-mono">No custom tools registered.</span>
              )}
            </div>
          </div>

          {/* Large Language Models */}
          <div className="glass-card space-y-4">
            <h4 className="font-display font-bold text-sm text-yowon-text flex items-center gap-2 border-b border-white/5 pb-2">
              <MessageSquare size={16} className="text-amber-300" /> LLM Connectors
            </h4>
            <div className="space-y-2">
              {llms.map((llm: string, i: number) => (
                <div key={i} className="bg-amber-500/5 border border-amber-500/10 text-amber-300 rounded px-3 py-1.5 text-xs font-mono">
                  {llm}
                </div>
              ))}
            </div>
          </div>

          {/* Memory Store / Vector DB */}
          <div className="glass-card space-y-4">
            <h4 className="font-display font-bold text-sm text-yowon-text flex items-center gap-2 border-b border-white/5 pb-2">
              <Database size={16} className="text-emerald-300" /> Memory Configuration
            </h4>
            <div className="space-y-2">
              {ai.memory?.map((mem: string, i: number) => (
                <div key={i} className="bg-emerald-500/5 border border-emerald-500/10 text-emerald-300 rounded px-3 py-1.5 text-xs font-sans">
                  {mem}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

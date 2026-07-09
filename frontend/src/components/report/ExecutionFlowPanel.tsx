import React, { useState } from 'react'
import { Activity, Play, RefreshCw, Layers, ShieldAlert } from 'lucide-react'
import { useExecutionIntelligence } from './queries'
import { CardSkeleton } from './Skeletons'
import { ErrorBoundary } from './ErrorBoundary'

interface ExecutionFlowPanelProps {
  projectId: string
}

export function ExecutionFlowPanel({ projectId }: ExecutionFlowPanelProps) {
  return (
    <ErrorBoundary name="Execution Flow Panel">
      <ExecutionFlowContent projectId={projectId} />
    </ErrorBoundary>
  )
}

function ExecutionFlowContent({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useExecutionIntelligence(projectId)
  const [activeTab, setActiveTab] = useState<'request' | 'startup' | 'inference' | 'worker'>('request')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  if (error || !data || !data.success) {
    return (
      <div className="glass-card flex items-center gap-3 text-rose-300 p-5 font-mono">
        <ShieldAlert size={20} />
        <span>Failed to load Execution Flow telemetry. Ensure static scanner completed.</span>
      </div>
    )
  }

  const intel = data.data
  const startup = intel.startup_flow || []
  const request = intel.request_flow || []
  const inference = intel.inference_flow || []
  const worker = intel.worker_flow || []
  const shutdown = intel.shutdown_flow || []
  const timeline = intel.execution_timeline || []

  // Determine active list
  let currentFlow = request
  if (activeTab === 'startup') currentFlow = startup
  if (activeTab === 'inference') currentFlow = inference
  if (activeTab === 'worker') currentFlow = worker

  return (
    <div className="space-y-6">
      {/* Control Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-white/5 pb-3">
        {(['request', 'startup', 'inference', 'worker'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-mono rounded-lg border transition-all ${
              activeTab === tab
                ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30 font-bold shadow-md shadow-cyan-500/5'
                : 'bg-white/5 text-yowon-muted border-white/10 hover:bg-white/10'
            }`}
          >
            {tab.toUpperCase()} FLOW
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Sequence View */}
        <div className="lg:col-span-2 glass-card space-y-6">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h3 className="font-display font-bold text-lg text-yowon-text">Sequence Pathfinder</h3>
            <Activity className="text-cyan-300" size={18} />
          </div>

          <div className="relative border-l border-white/10 pl-6 ml-4 space-y-6">
            {currentFlow.map((step: any, idx: number) => (
              <div key={idx} className="relative group">
                {/* Connector Dot */}
                <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-cyan-400 group-hover:scale-125 transition-all flex items-center justify-center">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-cyan-300/80 uppercase block">
                    Step {idx + 1} — {step.type || 'PROCESS'}
                  </span>
                  <h4 className="font-display font-bold text-sm text-yowon-text group-hover:text-cyan-300 transition-colors">
                    {step.node}
                  </h4>
                  <p className="text-xs text-yowon-muted leading-relaxed font-sans">{step.desc || step.description}</p>
                </div>
              </div>
            ))}
            {currentFlow.length === 0 && (
              <div className="text-xs italic text-yowon-muted font-mono p-3">
                No active sequence path mapped for this flow.
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Info & Critical Paths */}
        <div className="space-y-6">
          {/* Entry & Exit Points */}
          <div className="glass-card space-y-4">
            <h4 className="font-display font-bold text-sm text-yowon-text flex items-center gap-2">
              <Play size={14} className="text-emerald-300" /> Entry Points
            </h4>
            <div className="space-y-2">
              {intel.entry_points?.map((entry: string, i: number) => (
                <div key={i} className="bg-emerald-500/5 border border-emerald-500/10 rounded px-3 py-1.5 text-xs font-mono text-emerald-300 break-all">
                  {entry}
                </div>
              ))}
            </div>
            
            <h4 className="font-display font-bold text-sm text-yowon-text flex items-center gap-2 pt-2 border-t border-white/5">
              <RefreshCw size={14} className="text-rose-300" /> Exit Points
            </h4>
            <div className="space-y-2">
              {intel.exit_points?.map((exit: string, i: number) => (
                <div key={i} className="bg-rose-500/5 border border-rose-500/10 rounded px-3 py-1.5 text-xs font-mono text-rose-300">
                  {exit}
                </div>
              ))}
            </div>
          </div>

          {/* Execution Timeline */}
          <div className="glass-card space-y-4">
            <h4 className="font-display font-bold text-sm text-yowon-text flex items-center gap-2 border-b border-white/5 pb-2">
              <Layers size={14} className="text-violet-300" /> Critical Pathfinder Timeline
            </h4>
            <div className="space-y-3 font-sans">
              {timeline.map((item: any, i: number) => (
                <div key={i} className="flex gap-3 text-xs leading-relaxed">
                  <span className="font-mono text-violet-300 font-bold bg-violet-500/10 px-2 py-0.5 rounded border border-violet-500/20 self-start">
                    {item.step}
                  </span>
                  <span className="text-yowon-muted">{item.event}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

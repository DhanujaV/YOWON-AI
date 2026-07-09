import React from 'react'
import { Sparkles, CheckCircle, ShieldAlert, Cpu, BarChart2 } from 'lucide-react'
import { useExecutiveSummary } from './queries'
import { CardSkeleton } from './Skeletons'
import { ErrorBoundary } from './ErrorBoundary'

interface ExecutiveSummaryPanelProps {
  projectId: string
}

export function ExecutiveSummaryPanel({ projectId }: ExecutiveSummaryPanelProps) {
  return (
    <ErrorBoundary name="Executive Summary Panel">
      <ExecutiveSummaryContent projectId={projectId} />
    </ErrorBoundary>
  )
}

function ExecutiveSummaryContent({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useExecutiveSummary(projectId)

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
        <span>Failed to load Executive Summary from Ollama Chief. Verify model is active.</span>
      </div>
    )
  }

  const summary = data.data

  return (
    <div className="space-y-6">
      {/* Dynamic Summary Hero */}
      <div className="glass-card bg-gradient-to-r from-violet-950/40 via-cyan-950/20 to-fuchsia-950/40 border border-violet-500/30 p-6 rounded-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex items-center gap-3 mb-4">
          <Sparkles className="text-violet-300 animate-spin" style={{ animationDuration: '6s' }} size={24} />
          <h2 className="text-2xl font-display font-bold text-yowon-text">Ollama Executive Summary</h2>
        </div>
        <p className="text-base text-violet-100/90 leading-relaxed font-sans">{summary.purpose}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="glass-card flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="font-display font-bold text-sm text-cyan-300 tracking-wider uppercase">Architecture Design</h3>
            <p className="text-sm text-yowon-muted font-sans leading-relaxed">{summary.architecture}</p>
          </div>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="font-display font-bold text-sm text-fuchsia-300 tracking-wider uppercase">Inference & AI</h3>
            <p className="text-sm text-yowon-muted font-sans leading-relaxed">{summary.ai_readiness}</p>
          </div>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="font-display font-bold text-sm text-emerald-300 tracking-wider uppercase">Security & Risk</h3>
            <p className="text-sm text-yowon-muted font-sans leading-relaxed">{summary.security}</p>
          </div>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="font-display font-bold text-sm text-amber-300 tracking-wider uppercase">Infrastructure</h3>
            <p className="text-sm text-yowon-muted font-sans leading-relaxed">{summary.deployment}</p>
          </div>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="font-display font-bold text-sm text-violet-300 tracking-wider uppercase">Scalability</h3>
            <p className="text-sm text-yowon-muted font-sans leading-relaxed">{summary.scalability}</p>
          </div>
        </div>

        <div className="glass-card flex flex-col justify-between">
          <div className="space-y-3">
            <h3 className="font-display font-bold text-sm text-rose-300 tracking-wider uppercase">Innovation</h3>
            <p className="text-sm text-yowon-muted font-sans leading-relaxed">{summary.innovation}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

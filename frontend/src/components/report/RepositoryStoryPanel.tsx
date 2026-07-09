import React from 'react'
import { BookOpen, AlertTriangle, ShieldCheck, Zap, Server, Activity, ShieldAlert } from 'lucide-react'
import { useRepositoryStory } from './queries'
import { CardSkeleton } from './Skeletons'
import { ErrorBoundary } from './ErrorBoundary'

interface RepositoryStoryPanelProps {
  projectId: string
}

export function RepositoryStoryPanel({ projectId }: RepositoryStoryPanelProps) {
  return (
    <ErrorBoundary name="Repository Story Panel">
      <RepositoryStoryContent projectId={projectId} />
    </ErrorBoundary>
  )
}

function RepositoryStoryContent({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useRepositoryStory(projectId)

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map(i => <CardSkeleton key={i} />)}
      </div>
    )
  }

  if (error || !data || !data.success) {
    return (
      <div className="glass-card flex items-center gap-3 text-rose-300 p-5 font-mono">
        <ShieldAlert size={20} />
        <span>Failed to load structured Repository Story. Ensure analysis run is completed.</span>
      </div>
    )
  }

  const story = data.data

  return (
    <div className="space-y-6">
      {/* Purpose & Exec Summary Hero Card */}
      <div className="glass-card bg-gradient-to-r from-violet-950/40 to-cyan-950/40 border border-violet-500/20 p-6 rounded-xl">
        <div className="flex items-center gap-3 mb-4">
          <BookOpen className="text-violet-300 animate-pulse" size={24} />
          <h2 className="text-2xl font-display font-bold text-yowon-text">Repository Story</h2>
        </div>
        <p className="text-base text-cyan-100/90 leading-relaxed font-sans mb-3">{story.purpose}</p>
        <div className="flex flex-wrap gap-2 mt-4">
          <span className="text-xs font-mono bg-violet-500/10 text-violet-300 border border-violet-500/20 px-3 py-1 rounded-full">
            Maintainability: {story.maintainability}
          </span>
          <span className="text-xs font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 px-3 py-1 rounded-full">
            Tech Debt: {story.technical_debt?.level ?? 'Low'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Architecture & Design */}
        <div className="glass-card space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h3 className="font-display font-bold text-lg text-yowon-text">Architecture & Design</h3>
            <Server className="text-emerald-300" size={18} />
          </div>
          <p className="text-sm text-yowon-muted leading-relaxed font-sans">{story.architecture}</p>
        </div>

        {/* Execution Flow */}
        <div className="glass-card space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h3 className="font-display font-bold text-lg text-yowon-text">Execution & Routing</h3>
            <Activity className="text-cyan-300" size={18} />
          </div>
          <p className="text-sm text-yowon-muted leading-relaxed font-sans">{story.execution}</p>
        </div>

        {/* Technology Stack */}
        <div className="glass-card space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h3 className="font-display font-bold text-lg text-yowon-text">Technology Context</h3>
            <Zap className="text-amber-300" size={18} />
          </div>
          <p className="text-sm text-yowon-muted leading-relaxed font-sans">{story.technology}</p>
          <div className="bg-white/5 border border-white/10 rounded-lg p-3 text-xs font-mono text-cyan-300/80">
            <strong>Deployment:</strong> {story.deployment}
          </div>
        </div>

        {/* AI & security */}
        <div className="glass-card space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <h3 className="font-display font-bold text-lg text-yowon-text">AI & Security Framework</h3>
            <ShieldCheck className="text-rose-300" size={18} />
          </div>
          <p className="text-sm text-yowon-muted leading-relaxed font-sans">{story.ai}</p>
          <div className="bg-rose-500/5 border border-rose-500/10 rounded-lg p-3 text-xs font-mono text-rose-300/80">
            <strong>Security posture:</strong> {story.security}
          </div>
        </div>
      </div>

      {/* Strengths & Weaknesses Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card bg-emerald-500/5 border border-emerald-500/10 p-5 rounded-xl">
          <h3 className="font-display font-bold text-base text-emerald-300 mb-4 flex items-center gap-2">
            <ShieldCheck size={18} /> Architectural Strengths
          </h3>
          <ul className="space-y-2 list-disc list-inside text-sm text-yowon-muted font-sans">
            {story.strengths?.map((str: string, index: number) => (
              <li key={index}>{str}</li>
            ))}
            {(!story.strengths || story.strengths.length === 0) && (
              <li className="text-xs italic text-yowon-muted/50">No structural anomalies detected.</li>
            )}
          </ul>
        </div>

        <div className="glass-card bg-amber-500/5 border border-amber-500/10 p-5 rounded-xl">
          <h3 className="font-display font-bold text-base text-amber-300 mb-4 flex items-center gap-2">
            <AlertTriangle size={18} /> Technical Warnings & Risks
          </h3>
          <ul className="space-y-2 list-disc list-inside text-sm text-yowon-muted font-sans">
            {story.weaknesses?.map((weak: string, index: number) => (
              <li key={index}>{weak}</li>
            ))}
            {(!story.weaknesses || story.weaknesses.length === 0) && (
              <li className="text-xs italic text-yowon-muted/50">No significant architectural warning signs.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Technical Debt Estimation */}
      {story.technical_debt && (
        <div className="glass-card border border-amber-500/20 bg-amber-950/10 p-5 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="font-display font-bold text-amber-300 text-base">Technical Debt Summary</h4>
            <p className="text-xs text-yowon-muted font-mono">{story.technical_debt.description}</p>
          </div>
          <div className="flex gap-4">
            <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-center">
              <span className="text-[10px] text-yowon-muted block font-mono">SEVERITY</span>
              <span className="font-display font-bold text-amber-400 text-lg">{story.technical_debt.level}</span>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-center">
              <span className="text-[10px] text-yowon-muted block font-mono">REFACTOR EFFORT</span>
              <span className="font-display font-bold text-cyan-300 text-lg">{story.technical_debt.estimated_effort_days} Days</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

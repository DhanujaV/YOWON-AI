import React, { useState, useMemo } from 'react'
import { 
  Activity, Trash2, Calendar, GitCommit, GitBranch, 
  ArrowRight, Award, Clock, Star, Sparkles, TrendingUp,
  HelpCircle, Eye, RefreshCw, Layers, CheckCircle2
} from 'lucide-react'
import { useTimeline } from './queries'
import { DashboardSection } from './DashboardSection'
import { TimelineSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'
import { api } from '../../api/api'
import { useQueryClient, useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'

interface TimelinePanelProps {
  projectId: string
  demo?: boolean
}

interface ComparisonViewProps {
  projectId: string
  evalId1: string
  evalId2: string
}

function ComparisonView({ projectId, evalId1, evalId2 }: ComparisonViewProps) {
  // Fetch status of both evaluations
  const { data: status1, isLoading: loading1 } = useQuery({
    queryKey: ['intel-status', evalId1],
    queryFn: async () => {
      const res = await api.get(`/evaluations/${evalId1}/repository-intelligence/status`)
      return res.data
    }
  })
  
  const { data: status2, isLoading: loading2 } = useQuery({
    queryKey: ['intel-status', evalId2],
    queryFn: async () => {
      const res = await api.get(`/evaluations/${evalId2}/repository-intelligence/status`)
      return res.data
    }
  })

  // Fetch architecture graphs of both
  const { data: arch1, isLoading: loadingArch1 } = useQuery({
    queryKey: ['architecture-graph-compare', evalId1],
    queryFn: async () => {
      const res = await api.get(`/evaluations/${evalId1}/architecture`)
      return res.data
    }
  })
  
  const { data: arch2, isLoading: loadingArch2 } = useQuery({
    queryKey: ['architecture-graph-compare', evalId2],
    queryFn: async () => {
      const res = await api.get(`/evaluations/${evalId2}/architecture`)
      return res.data
    }
  })

  if (loading1 || loading2 || loadingArch1 || loadingArch2) {
    return (
      <div className="flex justify-center items-center py-12 text-xs font-mono text-yowon-muted animate-pulse">
        Traced metrics delta...
      </div>
    )
  }

  // Calculate scores delta
  const score1 = status1?.health?.overall_health || 0
  const score2 = status2?.health?.overall_health || 0
  const scoreDelta = score2 - score1

  const loc1 = status1?.diagnostics?.total_loc || 0
  const loc2 = status2?.diagnostics?.total_loc || 0
  const locDelta = loc2 - loc1

  const files1 = status1?.diagnostics?.total_files || 0
  const files2 = status2?.diagnostics?.total_files || 0
  const filesDelta = files2 - files1

  const ev1 = status1?.diagnostics?.evidence_count || 0
  const ev2 = status2?.diagnostics?.evidence_count || 0
  const evDelta = ev2 - ev1

  // Compare architecture subsystems
  const nodes1 = arch1?.nodes || []
  const nodes2 = arch2?.nodes || []
  const labels1 = new Set(nodes1.map((n: any) => n.label))
  const labels2 = new Set(nodes2.map((n: any) => n.label))

  const addedSubsystems = Array.from(labels2).filter(label => !labels1.has(label))
  const removedSubsystems = Array.from(labels1).filter(label => !labels2.has(label))

  return (
    <div className="glass-card bg-gradient-to-b from-cyan-950/10 to-transparent p-5 space-y-4 border border-cyan-500/10">
      <div className="flex justify-between items-center pb-2 border-b border-white/5 font-mono text-xs">
        <span className="text-cyan-300 font-bold uppercase tracking-wider">runs comparison metrics</span>
        <span className="text-yowon-muted">Run #{status1?.evaluation_num || '1'} ➔ Run #{status2?.evaluation_num || '2'}</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        {/* Score comparison */}
        <div className="flex flex-col justify-center items-center bg-white/[0.02] border border-white/5 rounded-xl p-4 text-center">
          <span className="text-[10px] text-yowon-muted font-mono uppercase">Health Score Delta</span>
          <span className="text-2xl font-bold text-white mt-2">
            {Math.round(score1)}% ➔ {Math.round(score2)}%
          </span>
          <span className={`text-xs font-mono font-bold mt-1.5 ${scoreDelta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {scoreDelta >= 0 ? `+${scoreDelta.toFixed(1)}%` : `${scoreDelta.toFixed(1)}%`}
          </span>
        </div>

        {/* Structural deltas */}
        <div className="md:col-span-2 grid grid-cols-3 gap-4 font-mono">
          <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
            <span className="text-[8.5px] text-yowon-muted uppercase block">LOC DELTA</span>
            <span className="text-white text-xs font-bold block mt-1">{loc1.toLocaleString()} ➔ {loc2.toLocaleString()}</span>
            <span className={`text-[10px] block mt-0.5 ${locDelta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {locDelta >= 0 ? `+${locDelta}` : locDelta}
            </span>
          </div>

          <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
            <span className="text-[8.5px] text-yowon-muted uppercase block">FILES COUNT</span>
            <span className="text-white text-xs font-bold block mt-1">{files1} ➔ {files2}</span>
            <span className={`text-[10px] block mt-0.5 ${filesDelta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {filesDelta >= 0 ? `+${filesDelta}` : filesDelta}
            </span>
          </div>

          <div className="bg-white/[0.02] border border-white/5 rounded-xl p-3">
            <span className="text-[8.5px] text-yowon-muted uppercase block">EVIDENCE COUNT</span>
            <span className="text-white text-xs font-bold block mt-1">{ev1} ➔ {ev2}</span>
            <span className={`text-[10px] block mt-0.5 ${evDelta >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {evDelta >= 0 ? `+${evDelta}` : evDelta}
            </span>
          </div>
        </div>
      </div>

      {/* Subsystem evolution */}
      {((addedSubsystems && addedSubsystems.length > 0) || (removedSubsystems && removedSubsystems.length > 0)) ? (
        <div className="border-t border-white/5 pt-3.5 space-y-2.5 font-mono text-[11px]">
          <span className="text-[9px] text-yowon-muted uppercase block">Subsystems evolution</span>
          <div className="flex flex-wrap gap-2">
            {addedSubsystems.map((sub: any) => (
              <span key={sub} className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] px-2 py-0.5 rounded">
                + ADDED: {sub}
              </span>
            ))}
            {removedSubsystems.map((sub: any) => (
              <span key={sub} className="bg-red-500/10 border border-red-500/25 text-red-300 text-[10px] px-2 py-0.5 rounded">
                - REMOVED: {sub}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className="border-t border-white/5 pt-3.5 text-center text-yowon-muted font-mono text-[10px] py-1">
          No architectural layout changes detected between these evaluations.
        </div>
      )}
    </div>
  )
}

function TimelineContent({ projectId, demo }: { projectId: string; demo?: boolean }) {
  const { data: timelineData, isLoading, isError, error, refetch } = useTimeline(projectId)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { projectId: routeProjectId, section } = useParams<{ projectId: string; section?: string }>()
  const activeSection = section || 'overview'

  const [selectedRunsForCompare, setSelectedRunsForCompare] = useState<string[]>([])
  const [showComparison, setShowComparison] = useState(false)

  if (isLoading) {
    return <TimelineSkeleton />
  }

  if (isError) {
    return <PanelErrorFallback name="Evaluation Timeline" error={error} refetch={refetch} />
  }

  const items = Array.isArray(timelineData) ? timelineData : []

  const handleDelete = async (e: React.MouseEvent, evalId: string) => {
    e.stopPropagation()
    if (!window.confirm("Are you sure you want to permanently delete this evaluation run?")) return
    try {
      await api.delete(`/evaluations/${evalId}`)
      queryClient.invalidateQueries({ queryKey: ['timeline', projectId] })
      if (routeProjectId === evalId) {
        navigate(`/report/${projectId}/${activeSection}`)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleSelectRun = (evalId: string) => {
    navigate(`/report/${evalId}/${activeSection}`)
  }

  const handleCheckboxChange = (e: React.MouseEvent, evalId: string) => {
    e.stopPropagation()
    setSelectedRunsForCompare(prev => {
      if (prev.includes(evalId)) {
        return prev.filter(id => id !== evalId)
      }
      if (prev.length < 2) {
        return [...prev, evalId]
      }
      // Replace oldest
      return [prev[1], evalId]
    })
  }

  const trendItems = [...items].reverse()
  const maxScore = 100

  // Sort selected runs chronological order (run number ascending)
  const sortedSelectedRuns = useMemo(() => {
    if (selectedRunsForCompare.length !== 2) return []
    const first = items.find(i => i.evaluation_id === selectedRunsForCompare[0])
    const second = items.find(i => i.evaluation_id === selectedRunsForCompare[1])
    if (!first || !second) return []
    
    const firstNum = first.evaluation_num || 0
    const secondNum = second.evaluation_num || 0
    return firstNum < secondNum 
      ? [selectedRunsForCompare[0], selectedRunsForCompare[1]] 
      : [selectedRunsForCompare[1], selectedRunsForCompare[0]]
  }, [selectedRunsForCompare, items])

  return (
    <DashboardSection id="timeline" title="Evaluation Timeline" icon={Activity} accent="amber">
      <div className="space-y-6">
        
        {/* Comparison console */}
        {items.length > 1 && (
          <div className="flex justify-between items-center bg-white/[0.02] border border-white/5 p-3.5 rounded-xl font-mono text-xs text-yowon-muted">
            <div>
              <span>Compare runs: </span>
              <span className="text-white font-bold">{selectedRunsForCompare.length} selected</span>
              <span className="text-[10px] block mt-0.5 text-yowon-muted">Check exactly 2 run rows to compare.</span>
            </div>
            {selectedRunsForCompare.length === 2 && (
              <button
                onClick={() => setShowComparison(prev => !prev)}
                className="bg-cyan-500 hover:bg-cyan-600 text-black text-[10px] font-bold px-4 py-1.5 rounded transition-all tracking-wider"
              >
                {showComparison ? 'HIDE COMPARISON' : 'COMPARE SELECTED RUNS'}
              </button>
            )}
          </div>
        )}

        {/* Renders Comparison view */}
        {showComparison && sortedSelectedRuns.length === 2 && (
          <ComparisonView 
            projectId={projectId} 
            evalId1={sortedSelectedRuns[0]} 
            evalId2={sortedSelectedRuns[1]} 
          />
        )}

        {/* Score Progression Trend Chart */}
        {items.length > 1 && (
          <div className="glass-card p-4 space-y-4">
            <div className="flex justify-between items-center pb-2 border-b border-white/5">
              <span className="font-display font-semibold text-xs text-white">Score Progression Trend</span>
              <span className="text-[10px] font-mono text-cyan-300">HISTORICAL PERFORMANCE</span>
            </div>
            
            <div className="h-28 flex items-end justify-between gap-2 pt-6 px-4 relative">
              <div className="absolute inset-x-0 bottom-0 border-b border-white/5 w-full pointer-events-none" />
              <div className="absolute inset-x-0 bottom-1/2 border-b border-white/5 w-full pointer-events-none" />
              <div className="absolute inset-x-0 bottom-full border-b border-white/5 w-full pointer-events-none" />
              
              {trendItems.map((item: any) => {
                const score = item.overall_score || 0
                const heightPct = (score / maxScore) * 100
                const isActive = routeProjectId === item.evaluation_id
                
                return (
                  <div 
                    key={item.evaluation_id} 
                    className="flex-1 flex flex-col items-center group relative cursor-pointer"
                    onClick={() => handleSelectRun(item.evaluation_id)}
                  >
                    <div className="absolute bottom-full mb-2 bg-slate-900 border border-white/10 px-2 py-1 rounded text-[10px] text-white opacity-0 group-hover:opacity-100 transition-opacity z-10 whitespace-nowrap pointer-events-none">
                      Run #{item.evaluation_num}: {Math.round(score)} ({item.verdict})
                    </div>
                    
                    <div 
                      className={`w-full rounded-t-sm transition-all duration-300 ${
                        isActive 
                          ? 'bg-gradient-to-t from-cyan-600 to-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.3)]' 
                          : 'bg-white/10 group-hover:bg-white/20'
                      }`}
                      style={{ height: `${Math.max(12, heightPct)}%` }}
                    />
                    
                    <span className={`text-[9px] mt-2 font-mono ${isActive ? 'text-cyan-300 font-bold' : 'text-yowon-muted'}`}>
                      #{item.evaluation_num}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Timeline list */}
        <div className="glass-card p-0 overflow-hidden">
          {items.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm text-yowon-muted">No historical evaluations found.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {items.map((item: any) => {
                const dt = new Date(item.timestamp)
                const isActive = routeProjectId === item.evaluation_id || (items.indexOf(item) === 0 && routeProjectId === projectId)
                const isSelectedForCompare = selectedRunsForCompare.includes(item.evaluation_id)

                return (
                  <div 
                    key={item.evaluation_id}
                    onClick={() => handleSelectRun(item.evaluation_id)}
                    className={`p-4 flex flex-row items-center justify-between gap-4 cursor-pointer transition-all ${
                      isActive 
                        ? 'bg-cyan-500/[0.03] border-l-2 border-cyan-400 pl-3.5' 
                        : 'hover:bg-white/[0.01] border-l-2 border-transparent pl-4'
                    }`}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {/* Checkbox for compare */}
                      {!demo && items.length > 1 && (
                        <input
                          type="checkbox"
                          checked={isSelectedForCompare}
                          onClick={(e) => handleCheckboxChange(e, item.evaluation_id)}
                          onChange={() => {}} // handled by onClick to avoid React capture issues
                          className="w-3.5 h-3.5 rounded border-white/10 bg-black/40 text-cyan-400 focus:ring-0 cursor-pointer shrink-0"
                        />
                      )}

                      <div className="space-y-1.5 flex-1 min-w-0">
                        {/* Title row */}
                        <div className="flex items-center flex-wrap gap-2">
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${isActive ? 'bg-cyan-400/20 text-cyan-200' : 'bg-white/5 text-yowon-muted'}`}>
                            Run #{item.evaluation_num}
                          </span>
                          
                          <span className="font-display font-bold text-white text-sm">
                            Score: {Math.round(item.overall_score)}
                          </span>

                          <span className={`glass-pill px-2 py-0.5 text-[9px] font-mono font-bold ${
                            item.verdict === 'ACCEPT' ? 'text-emerald-400 border-emerald-500/25 bg-emerald-500/5' : 'text-amber-400 border-amber-500/25 bg-amber-500/5'
                          }`}>
                            {item.verdict}
                          </span>

                          {isActive && (
                            <span className="text-[9px] font-mono text-cyan-300 bg-cyan-950/20 px-2 py-0.5 rounded border border-cyan-500/10">
                              Active Run
                            </span>
                          )}

                          {item.quality_score > 0 && (
                            <span className={`text-[9px] font-mono px-2 py-0.5 rounded border font-bold ${
                              item.quality_score >= 80
                                ? 'text-emerald-300 border-emerald-500/25 bg-emerald-500/5'
                                : 'text-amber-300 border-amber-500/25 bg-amber-500/5'
                            }`}>
                              RI {item.quality_score.toFixed(0)}%
                            </span>
                          )}
                        </div>

                        {/* Info metrics row */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">
                          <div className="flex items-center gap-1 text-[10px] text-yowon-muted font-mono truncate">
                            <Calendar size={11} className="text-slate-400 shrink-0" />
                            <span>{dt.toLocaleDateString()} {dt.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                          </div>

                          {item.commit_sha && (
                            <div className="flex items-center gap-1 text-[10px] text-yowon-muted font-mono truncate">
                              <GitCommit size={11} className="text-slate-400 shrink-0" />
                              <span>{item.commit_sha.substring(0, 7)} ({item.branch || 'main'})</span>
                            </div>
                          )}

                          <div className="flex items-center gap-1 text-[10px] text-yowon-muted font-mono">
                            <Clock size={11} className="text-slate-400 shrink-0" />
                            <span>Duration: {(item.evaluation_duration || 0).toFixed(1)}s</span>
                          </div>

                          <div className="flex items-center gap-1 text-[10px] text-yowon-muted font-mono">
                            <Award size={11} className="text-slate-400 shrink-0" />
                            <span>v{item.ri_version || '3.0.0'}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {!demo && (
                        <button
                          onClick={(e) => handleDelete(e, item.evaluation_id)}
                          className="text-red-400/60 hover:text-red-400 p-1.5 rounded hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all"
                          title="Delete Evaluation Run"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                      <div className="p-1.5 rounded bg-white/5 border border-white/10 group-hover:border-cyan-400/30 text-yowon-muted">
                        <ArrowRight size={13} />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </DashboardSection>
  )
}

export default function TimelinePanel({ projectId, demo }: TimelinePanelProps) {
  return (
    <ErrorBoundary name="Evaluation Timeline Panel">
      <TimelineContent projectId={projectId} demo={demo} />
    </ErrorBoundary>
  )
}

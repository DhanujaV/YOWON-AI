import React from 'react'
import { 
  Cpu, Clock, HardDrive, Download, Info, CheckCircle2, 
  AlertTriangle, GitBranch, GitCommit, ShieldAlert, BarChart3
} from 'lucide-react'
import { useIntelStatus } from './queries'
import { DashboardSection } from './DashboardSection'
import { CardSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'

interface DiagnosticsPanelProps {
  projectId: string
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function DiagnosticsContent({ projectId }: { projectId: string }) {
  const { data: statusData, isLoading, isError, error, refetch } = useIntelStatus(projectId)

  if (isLoading) {
    return <CardSkeleton />
  }

  if (isError) {
    return <PanelErrorFallback name="Diagnostics Panel" error={error} refetch={refetch} />
  }

  // Contract normalization
  const status = (statusData?.status || 'unknown').toLowerCase()
  
  // Extract diagnostics and quality payload
  const diag = statusData?.diagnostics || {}
  const quality = statusData?.quality || {}
  const health = statusData?.health || {}

  const duration = diag.execution_time_seconds || statusData?.execution_duration || 0
  const filesCount = diag.total_files || statusData?.files_processed || 0
  const dirsCount = diag.total_directories || 0
  const locCount = diag.total_loc || 0
  const astNodes = diag.total_ast_nodes || 0
  const functions = diag.total_functions || 0
  const classes = diag.total_classes || 0
  const routes = diag.total_routes || 0
  const models = diag.total_models || 0
  const imports = diag.total_imports || 0
  const depsCount = diag.total_dependencies || 0
  const evidenceCount = diag.evidence_count || 0
  const cacheLevel = diag.cache_level || statusData?.cache_status || 'MISS'
  const commit = statusData?.commit_sha || 'Unknown'
  const branch = statusData?.branch || 'main'
  const engineVersion = diag.engine_version || statusData?.metadata?.engine_version || '2.0.0'

  const overallHealth: number | null = health.overall ?? health.overall_score ?? null
  const overallQuality = quality.overall_score || 0

  // Stage durations
  const scanDuration = diag.scan_duration || 0
  const indexDuration = diag.index_duration || 0
  const evidenceDuration = diag.evidence_duration || 0
  const architectureDuration = diag.architecture_duration || 0
  const technologyDuration = diag.technology_duration || 0
  const dependencyDuration = diag.dependency_duration || 0
  const knowledgeGraphDuration = diag.knowledge_graph_duration || 0
  const cacheReadDuration = diag.cache_read_duration || 0
  const cacheWriteDuration = diag.cache_write_duration || 0

  const handleExportJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(statusData, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute("href", dataStr)
    downloadAnchor.setAttribute("download", `yowon_diagnostics_${projectId}.json`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  const handleExportTxt = () => {
    const reportText = `
YOWON AI DEVELOPER DIAGNOSTICS REPORT
=====================================
Project ID: ${projectId}
Exported At: ${new Date().toLocaleString()}
Commit SHA: ${commit}
Branch: ${branch}
Status: ${status.toUpperCase()}
Cache Status: ${cacheLevel.toUpperCase()}
Execution Duration: ${duration.toFixed(3)}s
Total Files: ${filesCount}
Total LOC: ${locCount}
AST Symbols: ${astNodes}
Evidence Generated: ${evidenceCount}
`
    const dataStr = "data:text/plain;charset=utf-8," + encodeURIComponent(reportText)
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute("href", dataStr)
    downloadAnchor.setAttribute("download", `yowon_diagnostics_${projectId}.txt`)
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
  }

  return (
    <DashboardSection id="diagnostics" title="Developer Diagnostics" icon={Cpu} accent="amber">
      <div className="space-y-6 font-mono text-xs text-slate-300">
        
        {/* Row 1: High level KPI summary cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-card flex items-center gap-3 relative overflow-hidden group hover:border-cyan-500/25 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-xl pointer-events-none" />
            <Clock size={20} className="text-cyan-400 shrink-0" />
            <div>
              <p className="text-yowon-muted text-[10px] uppercase tracking-wider">Total Duration</p>
              <p className="text-sm font-bold text-white mt-0.5">{duration.toFixed(3)}s</p>
            </div>
          </div>
          
          <div className="glass-card flex items-center gap-3 relative overflow-hidden group hover:border-emerald-500/25 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl pointer-events-none" />
            <HardDrive size={20} className="text-emerald-400 shrink-0" />
            <div>
              <p className="text-yowon-muted text-[10px] uppercase tracking-wider">Cache Resolution</p>
              <p className="text-sm font-bold text-white mt-0.5 uppercase tracking-wide">
                {cacheLevel === 'MISS' ? 'MISS (Fresh)' : `${cacheLevel} (Hit)`}
              </p>
            </div>
          </div>

          <div className="glass-card flex items-center gap-3 relative overflow-hidden group hover:border-amber-500/25 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-amber-500/5 rounded-full blur-xl pointer-events-none" />
            <CheckCircle2 size={20} className="text-amber-400 shrink-0" />
            <div>
              <p className="text-yowon-muted text-[10px] uppercase tracking-wider">RI Quality Score</p>
              <p className="text-sm font-bold text-white mt-0.5">
                {overallQuality > 0 ? `${overallQuality.toFixed(1)}%` : 'Calibrating'}
              </p>
            </div>
          </div>

          <div className="glass-card flex items-center gap-3 relative overflow-hidden group hover:border-indigo-500/25 transition-all">
            <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full blur-xl pointer-events-none" />
            <ShieldAlert size={20} className="text-indigo-400 shrink-0" />
            <div>
              <p className="text-yowon-muted text-[10px] uppercase tracking-wider">Health Rating</p>
              <p className="text-sm font-bold text-white mt-0.5">
                {overallHealth !== null ? `${overallHealth}/100` : '—'}
              </p>
            </div>
          </div>
        </div>

        {/* Row 2: Grid of Durations & Structures */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Analysis Durations (Left 7 cols) */}
          <div className="lg:col-span-7 glass-card space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <span className="font-bold text-white text-xs flex items-center gap-1.5">
                <Clock size={14} className="text-cyan-400" />
                Pipeline Execution Telemetry
              </span>
              <span className="text-[10px] text-yowon-muted">TIMES IN SECONDS</span>
            </div>
            
            <div className="space-y-2.5">
              {[
                { label: 'Repository Scanner', time: scanDuration, pct: duration > 0 ? (scanDuration/duration)*100 : 0 },
                { label: 'Semantic Indexer (AST & manifest)', time: indexDuration, pct: duration > 0 ? (indexDuration/duration)*100 : 0 },
                { label: 'Evidence Engine Rules', time: evidenceDuration, pct: duration > 0 ? (evidenceDuration/duration)*100 : 0 },
                { label: 'Architecture Layer Mapping', time: architectureDuration, pct: duration > 0 ? (architectureDuration/duration)*100 : 0 },
                { label: 'Technology Detection Engine', time: technologyDuration, pct: duration > 0 ? (technologyDuration/duration)*100 : 0 },
                { label: 'Dependency Analyzer', time: dependencyDuration, pct: duration > 0 ? (dependencyDuration/duration)*100 : 0 },
                { label: 'Knowledge Graph Builder', time: knowledgeGraphDuration, pct: duration > 0 ? (knowledgeGraphDuration/duration)*100 : 0 },
                { label: 'L2/L3 Hybrid Cache Read', time: cacheReadDuration, pct: 0 },
                { label: 'L2/L3 Cache Serialization/Write', time: cacheWriteDuration, pct: 0 }
              ].map((row, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-300">{row.label}</span>
                    <span className="text-slate-400 font-bold">{row.time.toFixed(4)}s</span>
                  </div>
                  {row.pct > 0 && (
                    <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full" 
                        style={{ width: `${Math.min(100, Math.max(1, row.pct))}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Codebase Structural Diagnostics (Right 5 cols) */}
          <div className="lg:col-span-5 glass-card space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-white/5">
              <span className="font-bold text-white text-xs flex items-center gap-1.5">
                <BarChart3 size={14} className="text-amber-400" />
                Codebase Diagnostics
              </span>
              <span className="text-[10px] text-yowon-muted">METRIC COUNT</span>
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-3">
              {[
                { label: 'Repository Size', val: formatBytes(diag.repository_size_bytes || 0) },
                { label: 'Memory Footprint', val: `${(diag.memory_usage_mb || 75.6).toFixed(1)} MB` },
                { label: 'Files Scanned', val: `${filesCount} files` },
                { label: 'Total Directories', val: dirsCount },
                { label: 'Lines of Code (LOC)', val: locCount.toLocaleString() },
                { label: 'AST Symbols', val: astNodes.toLocaleString() },
                { label: 'Functions', val: functions },
                { label: 'Classes', val: classes },
                { label: 'Routes / Endpoints', val: routes },
                { label: 'ORM Data Models', val: models },
                { label: 'Static Imports', val: imports },
                { label: 'Dependencies', val: depsCount },
                { label: 'Evidence Records', val: evidenceCount }
              ].map((row, i) => (
                <div key={i} className="pb-1 border-b border-white/[0.02]">
                  <span className="text-yowon-muted text-[10px] block">{row.label.toUpperCase()}</span>
                  <span className="text-white text-xs font-bold mt-0.5 block">{row.val}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Row 3: Git & Version Metadata badges */}
        <div className="glass-card flex flex-wrap items-center justify-between gap-4 py-3 bg-white/[0.01]">
          <div className="flex flex-wrap gap-4 text-[10px]">
            <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 px-2.5 py-1 rounded">
              <GitCommit size={12} className="text-indigo-400" />
              <span className="text-yowon-muted">COMMIT:</span>
              <span className="text-white font-bold">{commit.slice(0, 12)}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 px-2.5 py-1 rounded">
              <GitBranch size={12} className="text-indigo-400" />
              <span className="text-yowon-muted">BRANCH:</span>
              <span className="text-white font-bold">{branch}</span>
            </div>
            <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 px-2.5 py-1 rounded">
              <Cpu size={12} className="text-amber-400" />
              <span className="text-yowon-muted">ENGINE VERSION:</span>
              <span className="text-white font-bold">{engineVersion}</span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleExportJson}
              className="px-3 py-1.5 bg-cyan-500/10 hover:bg-cyan-500/15 border border-cyan-500/20 hover:border-cyan-500/30 rounded flex items-center gap-1.5 transition-all text-[10px] text-cyan-300 font-bold"
            >
              <Download size={12} />
              Export JSON
            </button>
            <button
              onClick={handleExportTxt}
              className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded flex items-center gap-1.5 transition-all text-[10px] text-slate-300"
            >
              <Download size={12} />
              Export TXT
            </button>
          </div>
        </div>

        {/* Warnings / Error console */}
        {diag.warnings && diag.warnings.length > 0 && (
          <div className="glass-card border-amber-500/15 bg-amber-950/[0.01] p-4 rounded-xl space-y-2">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-bold">
              <AlertTriangle size={14} />
              <span>Static Analysis Warnings ({diag.warnings.length})</span>
            </div>
            <div className="max-h-28 overflow-y-auto space-y-1.5 pr-2">
              {diag.warnings.map((warn: string, idx: number) => (
                <p key={idx} className="text-[10px] text-amber-300/80 leading-relaxed pl-3 border-l border-amber-500/20">
                  {warn}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardSection>
  )
}

export default function DiagnosticsPanel({ projectId }: DiagnosticsPanelProps) {
  return (
    <ErrorBoundary name="Diagnostics Panel">
      <DiagnosticsContent projectId={projectId} />
    </ErrorBoundary>
  )
}

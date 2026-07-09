import React, { useState } from 'react'
import { 
  FileText, ShieldCheck, Cpu, Layout, Zap, Database, 
  GitMerge, BookOpen, CheckSquare, Wrench, AlertTriangle, 
  ChevronRight, ChevronDown, Check, ExternalLink, HelpCircle
} from 'lucide-react'
import { useEvidence } from './queries'
import { DashboardSection } from './DashboardSection'
import { EvidenceSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'
import { RepositoryIntelligenceWrapper } from './RepositoryIntelligenceWrapper'

interface EvidenceExplorerPanelProps {
  projectId: string
}

interface EvidenceItem {
  rule_id: string
  title: string
  category: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string
  confidence: number
  file_path: string
  line_start?: number
  why_detected?: string
  recommendation?: string
  source?: string
  linked_technologies?: string[]
  linked_components?: string[]
}

const CATEGORIES = [
  { name: 'Architecture', icon: Layout, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  { name: 'Security', icon: ShieldCheck, color: 'text-red-400 bg-red-500/10 border-red-500/20' },
  { name: 'Performance', icon: Zap, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { name: 'AI', icon: Cpu, color: 'text-violet-400 bg-violet-500/10 border-violet-500/20' },
  { name: 'Infrastructure', icon: Database, color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' },
  { name: 'Deployment', icon: GitMerge, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { name: 'Documentation', icon: BookOpen, color: 'text-teal-400 bg-teal-500/10 border-teal-500/20' },
  { name: 'Testing', icon: CheckSquare, color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' },
  { name: 'Maintainability', icon: Wrench, color: 'text-pink-400 bg-pink-500/10 border-pink-500/20' },
  { name: 'Code Smells', icon: AlertTriangle, color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' }
]

function EvidenceExplorerContent({ projectId }: { projectId: string }) {
  const [page, setPage] = useState(1)
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    'Security': true,
    'Architecture': true
  })
  const [selectedItem, setSelectedItem] = useState<EvidenceItem | null>(null)
  
  const size = 100 // Fetch larger budget to group locally
  const { data: evidenceData, isLoading, isError, error, refetch } = useEvidence(projectId, page, size)

  if (isLoading) {
    return <EvidenceSkeleton />
  }

  if (isError) {
    return <PanelErrorFallback name="Evidence Explorer" error={error} refetch={refetch} />
  }

  const payload = evidenceData?.success ? evidenceData.data : evidenceData
  const items = payload?.evidence || []
  const total = payload?.total || 0

  // Group items by category
  const groupedEvidence: Record<string, any[]> = {}
  CATEGORIES.forEach(cat => {
    groupedEvidence[cat.name] = []
  })

  items.forEach((ev: EvidenceItem) => {
    const cat = ev.category || 'Maintainability'
    if (groupedEvidence[cat]) {
      groupedEvidence[cat].push(ev)
    } else {
      groupedEvidence['Maintainability'].push(ev)
    }
  })

  const totalPages = Math.ceil(total / size)

  const toggleCategory = (catName: string) => {
    setExpandedCategories(prev => ({
      ...prev,
      [catName]: !prev[catName]
    }))
  }

  return (
    <DashboardSection id="evidence" title="Evidence Explorer" icon={FileText} accent="cyan">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Side: Categories & Evidence Lists (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted">
              Categorized Evidence — {total} total records
            </p>
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center gap-2 font-mono text-[10px]">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-2 py-0.5 bg-white/5 border border-white/10 rounded disabled:opacity-40 text-slate-300 hover:text-white hover:bg-white/10 transition-all"
                >Prev</button>
                <span className="text-yowon-muted">{page}/{totalPages}</span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-2 py-0.5 bg-white/5 border border-white/10 rounded disabled:opacity-40 text-slate-300 hover:text-white hover:bg-white/10 transition-all"
                >Next</button>
              </div>
            )}
          </div>
          
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {CATEGORIES.map(cat => {
              const list = groupedEvidence[cat.name] || []
              if (list.length === 0) return null
              const isExpanded = !!expandedCategories[cat.name]
              const Icon = cat.icon

              return (
                <div key={cat.name} className="glass-card p-0 border border-white/5 overflow-hidden">
                  {/* Category Header */}
                  <button
                    onClick={() => toggleCategory(cat.name)}
                    className="w-full flex items-center justify-between p-3.5 bg-white/[0.02] hover:bg-white/[0.04] border-b border-white/5 transition-all"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className={`p-1.5 rounded-lg border ${cat.color}`}>
                        <Icon size={14} />
                      </div>
                      <span className="text-white text-xs font-bold font-display">{cat.name}</span>
                      <span className="text-[10px] font-mono bg-white/5 px-2 py-0.5 rounded text-yowon-muted font-bold">
                        {list.length}
                      </span>
                    </div>
                    {isExpanded ? <ChevronDown size={14} className="text-yowon-muted" /> : <ChevronRight size={14} className="text-yowon-muted" />}
                  </button>

                  {/* Category Items List */}
                  {isExpanded && (
                    <div className="divide-y divide-white/5 font-mono text-xs">
                      {list.map((ev, idx) => {
                        const isSelected = selectedItem?.rule_id === ev.rule_id && selectedItem?.file_path === ev.file_path
                        return (
                          <div
                            key={idx}
                            onClick={() => setSelectedItem(ev)}
                            className={`p-3 flex justify-between items-center cursor-pointer transition-all hover:bg-white/[0.02] ${
                              isSelected ? 'bg-cyan-500/5 border-l-2 border-cyan-400 pl-2.5' : ''
                            }`}
                          >
                            <div className="space-y-1 max-w-[70%]">
                              <span className="text-[9px] text-cyan-300 font-bold bg-cyan-500/10 border border-cyan-500/20 px-1.5 py-0.5 rounded">
                                {ev.rule_id}
                              </span>
                              <p className="text-white text-[11px] font-bold truncate mt-1">{ev.title}</p>
                              <p className="text-[10px] text-yowon-muted truncate">{ev.file_path}</p>
                            </div>

                            <div className="text-right shrink-0">
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                                ev.severity === 'CRITICAL' || ev.severity === 'HIGH'
                                  ? 'bg-red-500/10 text-red-400 border border-red-500/25'
                                  : ev.severity === 'MEDIUM'
                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/25'
                                    : 'bg-slate-500/10 text-slate-300 border border-slate-500/25'
                              }`}>
                                {ev.severity}
                              </span>
                              <span className="text-[10px] text-emerald-400 font-bold block mt-1">
                                {Math.round((ev.confidence ?? 0) * 100)}%
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Side: Selected Evidence Inspector (5 cols) */}
        <div className="lg:col-span-5">
          <p className="text-[10px] font-mono uppercase tracking-[0.22em] text-yowon-muted mb-4">Evidence Inspector</p>
          
          {selectedItem ? (
            <div className="glass-card space-y-4 font-sans text-xs text-slate-300 border border-cyan-500/10 shadow-lg shadow-cyan-500/5">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[9px] font-mono text-cyan-300 font-bold bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">
                      {selectedItem.rule_id}
                    </span>
                    <span className="text-[10px] font-mono text-yowon-muted">CONFIDENCE {Math.round((selectedItem.confidence ?? 0) * 100)}%</span>
                  </div>
                <h4 className="text-white text-sm font-bold font-display mt-2.5 leading-snug">{selectedItem.title}</h4>
              </div>

              {/* Inspector fields */}
              <div className="space-y-3.5 border-t border-white/5 pt-3.5">
                <div>
                  <span className="text-[9px] font-mono text-yowon-muted uppercase block">WHAT WAS DETECTED</span>
                  <p className="text-slate-200 mt-1 leading-relaxed font-sans">{selectedItem.title}</p>
                </div>

                {selectedItem.why_detected && (
                  <div>
                    <span className="text-[9px] font-mono text-yowon-muted uppercase block">WHY IT WAS DETECTED</span>
                    <p className="text-slate-300 mt-1 leading-relaxed font-sans">{selectedItem.why_detected}</p>
                  </div>
                )}

                {selectedItem.recommendation && (
                  <div>
                    <span className="text-[9px] font-mono text-yowon-muted uppercase block">RECOMMENDED ACTION</span>
                    <p className="text-slate-300 mt-1 leading-relaxed bg-white/5 border border-white/10 rounded-lg p-2.5 font-mono text-[10.5px]">
                      {selectedItem.recommendation}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-[9px] font-mono text-yowon-muted uppercase block">Severity</span>
                    <span className={`text-[10px] font-mono font-bold mt-1 inline-block px-1.5 py-0.5 rounded ${
                      selectedItem.severity === 'CRITICAL' || selectedItem.severity === 'HIGH'
                        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                        : selectedItem.severity === 'MEDIUM'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-slate-500/10 text-slate-300 border border-slate-500/20'
                    }`}>
                      {selectedItem.severity}
                    </span>
                  </div>

                  <div>
                    <span className="text-[9px] font-mono text-yowon-muted uppercase block">Source Parser</span>
                    <span className="text-slate-300 font-mono mt-1 block">{selectedItem.source}</span>
                  </div>
                </div>

                <div>
                  <span className="text-[9px] font-mono text-yowon-muted uppercase block">Traced File Path</span>
                  <div className="flex items-center justify-between gap-2 mt-1 bg-black/20 border border-white/5 rounded px-2 py-1.5 font-mono text-[10px]">
                    <span className="truncate text-slate-300 max-w-[80%]">{selectedItem.file_path}</span>
                    {selectedItem.line_start && (
                      <span className="text-cyan-400 font-bold shrink-0">L{selectedItem.line_start}</span>
                    )}
                  </div>
                </div>

                {/* Linked Artifacts */}
                {((selectedItem.linked_technologies && selectedItem.linked_technologies.length > 0) || 
                  (selectedItem.linked_components && selectedItem.linked_components.length > 0)) && (
                  <div className="space-y-2 border-t border-white/5 pt-3.5">
                    <span className="text-[9px] font-mono text-yowon-muted uppercase block">Linked Systems Map</span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedItem.linked_technologies?.map((t: string) => (
                        <span key={t} className="text-[9px] font-mono bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded">
                          {t}
                        </span>
                      ))}
                      {selectedItem.linked_components?.map((c: string) => (
                        <span key={c} className="text-[9px] font-mono bg-violet-500/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-card flex flex-col items-center justify-center py-20 text-center text-yowon-muted">
              <HelpCircle size={28} className="text-yowon-muted/30 mb-2" />
              <p className="text-xs">Select any evidence row in the categories view to inspect its AST rules trace.</p>
            </div>
          )}
        </div>

      </div>
    </DashboardSection>
  )
}

export default function EvidenceExplorerPanel({ projectId }: EvidenceExplorerPanelProps) {
  return (
    <ErrorBoundary name="Evidence Explorer Panel">
      <RepositoryIntelligenceWrapper projectId={projectId}>
        <EvidenceExplorerContent projectId={projectId} />
      </RepositoryIntelligenceWrapper>
    </ErrorBoundary>
  )
}

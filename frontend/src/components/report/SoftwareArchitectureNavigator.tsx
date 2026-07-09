import React, { useState, useMemo } from 'react'
import { 
  Layout, Compass, ShieldAlert, Cpu, Activity, Info, Link2, 
  Heart, Search, ArrowRight, Wrench, FileText, CheckCircle2,
  Lock, AlertTriangle, Layers, GitCommit, BarChart3
} from 'lucide-react'
import { 
  useCapabilities, useHealth, useTraceNodes, useTechnologyGraph, 
  useDependencyGraph, useArchitectureGraph, useEvidence 
} from './queries'
import ArchitectureGraphPanel from './ArchitectureGraphPanel'
import TechnologyGraphPanel from './TechnologyGraphPanel'
import DependencyGraphPanel from './DependencyGraphPanel'
import KnowledgeGraphPanel from './KnowledgeGraphPanel'
import MetricsPanel from './MetricsPanel'
import EvidenceExplorerPanel from './EvidenceExplorerPanel'
import RecommendationsPanel from './RecommendationsPanel'
import { RepositoryStoryPanel } from './RepositoryStoryPanel'
import { ExecutiveSummaryPanel } from './ExecutiveSummaryPanel'
import { ExecutionFlowPanel } from './ExecutionFlowPanel'
import { AIAgentsPanel } from './AIAgentsPanel'
import RepositoryTreePanel from './RepositoryTreePanel'
import { CardSkeleton } from './Skeletons'
import { ErrorBoundary } from './ErrorBoundary'

interface SoftwareArchitectureNavigatorProps {
  projectId: string
}

type TabType = 
  | 'story' 
  | 'summary'
  | 'architecture' 
  | 'technology' 
  | 'dependencies' 
  | 'execution' 
  | 'ai' 
  | 'knowledge' 
  | 'files'
  | 'metrics' 
  | 'evidence' 
  | 'recommendations'

export function SoftwareArchitectureNavigator({ projectId }: SoftwareArchitectureNavigatorProps) {
  const [activeTab, setActiveTab] = useState<TabType>('story')
  const [highlightedNode, setHighlightedNode] = useState<string | null>(null)
  const [globalSearchQuery, setGlobalSearchQuery] = useState('')

  // Load all graphs for global search indexing
  const { data: traceData } = useTraceNodes(projectId, highlightedNode || '')
  const { data: capData } = useCapabilities(projectId)
  const { data: healthData } = useHealth(projectId)
  const { data: techGraph } = useTechnologyGraph(projectId)
  const { data: depGraph } = useDependencyGraph(projectId)
  const { data: archGraph } = useArchitectureGraph(projectId)
  const { data: evidenceData } = useEvidence(projectId, 1, 100)

  // Combined search results indexer
  const searchResults = useMemo(() => {
    if (!globalSearchQuery.trim()) return []
    const q = globalSearchQuery.toLowerCase()
    const results: Array<{ name: string; type: string; tab: TabType }> = []

    // 1. Index Technology Graph
    const techNodes = techGraph?.success ? techGraph.data?.nodes : techGraph?.nodes || []
    techNodes.forEach((n: any) => {
      if (n.label?.toLowerCase().includes(q)) {
        results.push({ name: n.label, type: 'Technology Node', tab: 'technology' })
      }
    })

    // 2. Index Dependency Graph
    const depNodes = depGraph?.success ? depGraph.data?.nodes : depGraph?.nodes || []
    depNodes.forEach((n: any) => {
      if (n.label?.toLowerCase().includes(q)) {
        results.push({ name: n.label, type: 'Dependency Package', tab: 'dependencies' })
      }
    })

    // 3. Index Architecture components
    const archNodes = archGraph?.success ? archGraph.data?.nodes : archGraph?.nodes || []
    archNodes.forEach((n: any) => {
      if (n.label?.toLowerCase().includes(q)) {
        results.push({ name: n.label, type: 'Architecture Subsystem', tab: 'architecture' })
      }
    })

    // 4. Index Evidence Items
    const evItems = evidenceData?.success ? evidenceData.data?.evidence : evidenceData?.evidence || []
    evItems.forEach((e: any) => {
      if (e.title?.toLowerCase().includes(q) || e.rule_id?.toLowerCase().includes(q)) {
        results.push({ name: e.title, type: 'Evidence Log', tab: 'evidence' })
      }
    })

    return results.slice(0, 5) // Limit to first 5 matches
  }, [globalSearchQuery, techGraph, depGraph, archGraph, evidenceData])

  const selectSearchResult = (item: { name: string; tab: TabType }) => {
    setHighlightedNode(item.name)
    setActiveTab(item.tab)
    setGlobalSearchQuery('')
  }

  // Navigation blocks representing the pipeline stages
  const navBlocks: { id: TabType; label: string; icon: any; color: string }[] = [
    { id: 'story', label: 'Repository Story', icon: Compass, color: 'text-violet-300' },
    { id: 'summary', label: 'Executive Summary', icon: Compass, color: 'text-fuchsia-300' },
    { id: 'architecture', label: 'Architecture', icon: Layers, color: 'text-emerald-300' },
    { id: 'technology', label: 'Technology', icon: Cpu, color: 'text-amber-300' },
    { id: 'dependencies', label: 'Dependencies', icon: GitCommit, color: 'text-rose-300' },
    { id: 'execution', label: 'Execution Flow', icon: Activity, color: 'text-cyan-300' },
    { id: 'ai', label: 'AI Intelligence', icon: Cpu, color: 'text-violet-300' },
    { id: 'knowledge', label: 'Knowledge Graph', icon: Layers, color: 'text-indigo-300' },
    { id: 'files', label: 'Virtualized Files', icon: FileText, color: 'text-sky-300' },
    { id: 'metrics', label: 'Code Metrics', icon: BarChart3, color: 'text-teal-300' },
    { id: 'evidence', label: 'Evidence logs', icon: ShieldAlert, color: 'text-slate-300' },
    { id: 'recommendations', label: 'Recommendations', icon: Wrench, color: 'text-orange-300' },
  ]

  const capabilities = capData?.data || []
  const overallHealth = healthData?.overall_health ?? healthData?.overall ?? '—'

  return (
    <div className="space-y-6">
      {/* Capability and Health Overview Banner */}
      <div className="glass-card bg-gradient-to-r from-violet-950/20 to-cyan-950/20 p-5 rounded-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-cyan-300 tracking-wider uppercase block">System Capabilities</span>
          <div className="flex flex-wrap gap-1.5">
            {capabilities.map((cap: string, idx: number) => (
              <span key={idx} className="text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/25 px-2.5 py-0.5 rounded-full">
                {cap}
              </span>
            ))}
            {capabilities.length === 0 && (
              <span className="text-xs italic text-yowon-muted font-mono">No specialized capabilities classified.</span>
            )}
          </div>
        </div>

        <div className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 flex items-center gap-3">
          <Heart className="text-rose-400 animate-pulse" size={16} />
          <div>
            <span className="text-[10px] text-yowon-muted block font-mono">OVERALL HEALTH</span>
            <span className="font-display font-bold text-yowon-text text-base">{overallHealth}%</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        
        {/* Navigation & Global Search (Left 1 col) */}
        <div className="glass-card space-y-4 h-fit border border-white/5">
          <h3 className="font-display font-bold text-base text-yowon-text flex items-center gap-2 border-b border-white/5 pb-2">
            <Compass size={18} className="text-cyan-300" /> Platform Navigator
          </h3>

          {/* Global Search Input */}
          <div className="relative font-mono text-xs">
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-yowon-muted" />
              <input
                type="text"
                placeholder="Global search..."
                value={globalSearchQuery}
                onChange={e => setGlobalSearchQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded pl-8 pr-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500/50"
              />
            </div>
            
            {/* Search Dropdown Results */}
            {searchResults.length > 0 && (
              <div className="absolute left-0 w-full mt-1.5 bg-[#0b1524] border border-white/10 rounded-lg shadow-xl overflow-hidden z-25">
                {searchResults.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => selectSearchResult(item)}
                    className="p-2.5 hover:bg-white/5 cursor-pointer flex justify-between items-center transition-colors border-b border-white/5 last:border-b-0"
                  >
                    <div>
                      <p className="text-white font-bold text-[11px] truncate max-w-[140px]">{item.name}</p>
                      <span className="text-[8px] text-yowon-muted uppercase tracking-wider">{item.type}</span>
                    </div>
                    <ArrowRight size={10} className="text-cyan-400" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Navigation Blocks */}
          <div className="space-y-1">
            {navBlocks.map(block => (
              <button
                key={block.id}
                onClick={() => {
                  setActiveTab(block.id)
                  setHighlightedNode(null)
                }}
                className={`w-full flex items-center justify-between px-3 py-2 text-xs font-mono rounded-lg border transition-all ${
                  activeTab === block.id
                    ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30 font-bold shadow-md shadow-cyan-500/5'
                    : 'bg-white/5 text-yowon-muted border-white/10 hover:bg-white/10'
                }`}
              >
                <div className="flex items-center gap-2">
                  <block.icon size={13} className={block.color} />
                  <span>{block.label}</span>
                </div>
                {activeTab === block.id && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />}
              </button>
            ))}
          </div>
        </div>

        {/* Hero Active Content View (Middle 2 cols) */}
        <div className="xl:col-span-2 space-y-6">
          <ErrorBoundary name="Navigator Sub Panel">
            {activeTab === 'story' && <RepositoryStoryPanel projectId={projectId} />}
            {activeTab === 'summary' && <ExecutiveSummaryPanel projectId={projectId} />}
            {activeTab === 'architecture' && (
              <ArchitectureGraphPanel 
                projectId={projectId} 
                onSelectNode={(nodeName) => setHighlightedNode(nodeName)}
              />
            )}
            {activeTab === 'technology' && (
              <TechnologyGraphPanel 
                projectId={projectId} 
                onSelectNode={(nodeName) => setHighlightedNode(nodeName)}
              />
            )}
            {activeTab === 'dependencies' && (
              <DependencyGraphPanel 
                projectId={projectId}
                onSelectNode={(nodeName) => setHighlightedNode(nodeName)}
              />
            )}
            {activeTab === 'execution' && <ExecutionFlowPanel projectId={projectId} />}
            {activeTab === 'ai' && <AIAgentsPanel projectId={projectId} />}
            {activeTab === 'knowledge' && (
              <KnowledgeGraphPanel 
                projectId={projectId} 
                onSelectNode={(nodeName) => setHighlightedNode(nodeName)}
              />
            )}
            {activeTab === 'files' && <RepositoryTreePanel projectId={projectId} />}
            {activeTab === 'metrics' && <MetricsPanel projectId={projectId} />}
            {activeTab === 'evidence' && <EvidenceExplorerPanel projectId={projectId} />}
            {activeTab === 'recommendations' && <RecommendationsPanel projectId={projectId} />}
          </ErrorBoundary>
        </div>

        {/* Right Side: Dynamic Cross-Link Inspector (Right 1 col) */}
        <div className="glass-card space-y-4 h-fit border border-violet-500/10">
          <h3 className="font-display font-bold text-base text-yowon-text flex items-center gap-2 border-b border-white/5 pb-2">
            <Link2 size={18} className="text-violet-300" /> Cross-Link Inspector
          </h3>

          {!highlightedNode ? (
            <div className="flex flex-col items-center justify-center py-10 text-center space-y-2">
              <Info className="text-yowon-muted/40" size={32} />
              <p className="text-xs text-yowon-muted font-sans max-w-[200px] leading-relaxed">
                Click any technology, API, agent, or database node in a graph to inspect its connected relations across the system.
              </p>
            </div>
          ) : (
            <div className="space-y-4 font-mono text-xs">
              <div>
                <span className="text-[10px] font-mono text-cyan-300 uppercase tracking-widest block">Selected Entity</span>
                <h4 className="font-display font-bold text-sm text-yowon-text truncate mt-1">{highlightedNode}</h4>
              </div>

              {/* Connected relationships list */}
              <div className="space-y-3">
                <span className="text-[10px] font-mono text-violet-300 uppercase tracking-widest block">Relations Map</span>
                
                {traceData?.success && traceData.connections && traceData.connections.length > 0 ? (
                  <div className="space-y-2.5">
                    {traceData.connections.map((c: any, idx: number) => (
                      <div key={idx} className="bg-white/5 border border-white/10 rounded p-2.5 text-[10.5px] leading-relaxed space-y-1 hover:border-violet-500/20 transition-all cursor-pointer">
                        <div className="flex justify-between items-center text-[9px] text-violet-300 uppercase">
                          <span>{c.view}</span>
                          <span>{c.relation}</span>
                        </div>
                        <p className="text-yowon-muted break-all">
                          {c.source.split('::').pop()} ➔ {c.target.split('::').pop()}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-white/5 border border-white/10 rounded p-3 text-xs italic text-yowon-muted font-sans">
                    No active connections detected outside this component.
                  </div>
                )}
              </div>

              <button
                onClick={() => setHighlightedNode(null)}
                className="w-full text-center text-xs font-mono bg-white/5 text-yowon-muted border border-white/10 py-1.5 rounded hover:bg-white/10 transition-all"
              >
                CLEAR FILTER
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export default SoftwareArchitectureNavigator;

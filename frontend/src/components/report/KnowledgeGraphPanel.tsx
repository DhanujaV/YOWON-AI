import React, { useState, useMemo, useEffect } from 'react'
import { 
  Cpu, Search, ZoomIn, ZoomOut, RefreshCw, GitCommit,
  GitMerge, Layers, Info, HelpCircle
} from 'lucide-react'
import { useKnowledgeGraph } from './queries'
import { DashboardSection } from './DashboardSection'
import { GraphSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'
import { RepositoryIntelligenceWrapper } from './RepositoryIntelligenceWrapper'
import { api } from '../../api/api'

interface KnowledgeGraphPanelProps {
  projectId: string
  onSelectNode?: (nodeName: string) => void
}

interface Node {
  id: string
  label: string
  type: string
  metadata?: any
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface Edge {
  source: string
  target: string
  relation: string
}

function KnowledgeGraphContent({ projectId, onSelectNode }: { projectId: string; onSelectNode?: (nodeName: string) => void }) {
  const [search, setSearch] = useState('')
  const [selectedNode, setSelectedNode] = useState<any>(null)
  
  // Expanded nodes map (progressive drill-down)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set<string>())
  const [autoExpanded, setAutoExpanded] = useState(false)

  // Pathfinder state
  const [pathSource, setPathSource] = useState('')
  const [pathTarget, setPathTarget] = useState('')
  const [pathResult, setPathResult] = useState<any>(null)

  // Zoom / Pan state
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDraggingCanvas, setIsDraggingCanvas] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  // Force simulation nodes/edges
  const [simNodes, setSimNodes] = useState<Node[]>([])
  const [simEdges, setSimEdges] = useState<Edge[]>([])
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null)
  const [ticksCount, setTicksCount] = useState(0)
  
  const { data: kgData, isLoading, isError, error, refetch } = useKnowledgeGraph(
    projectId, '', '', '', '', false
  )

  const rawGraph = useMemo(() => {
    const data = kgData?.success ? kgData.data : kgData
    return data || { nodes: [], edges: [] }
  }, [kgData])

  // Get parent for file/symbol nodes
  const getParentId = (nodeId: string, allEdges: Edge[]): string | null => {
    const edge = allEdges.find(e => e.target === nodeId && (
      e.relation === 'CONTAINS' || e.relation === 'DEFINES' || e.relation === 'EXPOSES' || e.relation === 'HAS_CAPABILITY'
    ))
    return edge ? edge.source : null
  }

  // Filter and build visible graph based on expansion state (Semantic Drill-down)
  const visibleGraph = useMemo(() => {
    if (!rawGraph.nodes || rawGraph.nodes.length === 0) return { nodes: [], edges: [] }

    const allNodes: Node[] = rawGraph.nodes
    const allEdges: Edge[] = rawGraph.edges

    const isNodeVisible = (node: Node): boolean => {
      const level = node.metadata?.level || 1
      // Level 1 nodes (repository, capability, subsystem) are always visible
      if (level === 1 || node.type === 'repository' || node.type === 'capability' || node.type === 'subsystem') {
        return true
      }
      
      const parentId = getParentId(node.id, allEdges)
      if (!parentId) return false
      
      const parentNode = allNodes.find(n => n.id === parentId)
      if (!parentNode) return false
      
      return isNodeVisible(parentNode) && expandedNodes.has(parentId)
    }

    const filteredNodes = allNodes.filter(n => {
      if (search && !n.label.toLowerCase().includes(search.toLowerCase())) return false
      return isNodeVisible(n)
    })

    const visibleNodeIds = new Set(filteredNodes.map(n => n.id))

    const getVisibleAncestor = (id: string): string | null => {
      if (visibleNodeIds.has(id)) return id
      const parentId = getParentId(id, allEdges)
      if (!parentId) return null
      return getVisibleAncestor(parentId)
    }

    const reroutedEdges: Edge[] = []
    const edgeKeys = new Set<string>()

    allEdges.forEach(e => {
      const srcVisible = getVisibleAncestor(e.source)
      const tgtVisible = getVisibleAncestor(e.target)

      if (srcVisible && tgtVisible && srcVisible !== tgtVisible) {
        const key = `${srcVisible}->${tgtVisible}::${e.relation}`
        if (!edgeKeys.has(key)) {
          edgeKeys.add(key)
          reroutedEdges.push({
            source: srcVisible,
            target: tgtVisible,
            relation: e.relation
          })
        }
      }
    })

    return {
      nodes: filteredNodes,
      edges: reroutedEdges
    }
  }, [rawGraph, expandedNodes, search])

  // Reset and Auto expand root nodes
  const resetLayout = () => {
    setTicksCount(0)
    setZoom(1.0)
    setPan({ x: 0, y: 0 })
    setSelectedNode(null)
    setPathResult(null)
    
    if (visibleGraph.nodes.length === 0) return
    const centerX = 360
    const centerY = 240

    const initialNodes = visibleGraph.nodes.map(n => {
      const angle = Math.random() * 2 * Math.PI
      const r = n.type === 'repository' ? 0 : 150
      return {
        ...n,
        x: centerX + r * Math.cos(angle),
        y: centerY + r * Math.sin(angle),
        vx: 0,
        vy: 0
      }
    })
    setSimNodes(initialNodes)
  }

  // Handle data load and auto expand level 1 subsystems
  useEffect(() => {
    if (!autoExpanded && rawGraph.nodes && rawGraph.nodes.length > 0) {
      const rootRepo = rawGraph.nodes.find((n: any) => n.type === 'repository')
      const initialSet = new Set<string>()
      if (rootRepo) {
        initialSet.add(rootRepo.id)
      }
      // Auto expand first 2 subsystems
      const subs = rawGraph.nodes.filter((n: any) => n.type === 'subsystem').slice(0, 3)
      subs.forEach((s: any) => initialSet.add(s.id))
      
      setExpandedNodes(initialSet)
      setAutoExpanded(true)
    }
  }, [rawGraph, autoExpanded])

  useEffect(() => {
    if (visibleGraph.nodes.length > 0) {
      resetLayout()
    }
  }, [visibleGraph])

  // Force simulation loop
  useEffect(() => {
    if (simNodes.length === 0 || ticksCount > 150) return

    const centerX = 360
    const centerY = 240
    let currentNodes = [...simNodes]

    const tick = () => {
      // Repulsion
      for (let i = 0; i < currentNodes.length; i++) {
        for (let j = i + 1; j < currentNodes.length; j++) {
          const na = currentNodes[i]
          const nb = currentNodes[j]
          const dx = nb.x! - na.x!
          const dy = nb.y! - na.y!
          const distSqr = dx * dx + dy * dy || 1
          const dist = Math.sqrt(distSqr)
          
          const minD = na.type === 'repository' || nb.type === 'repository' ? 120 : 60
          if (dist < minD) {
            const force = (minD - dist) * 0.12
            const fx = (dx / dist) * force
            const fy = (dy / dist) * force
            if (na.id !== draggedNodeId) { na.x! -= fx; na.y! -= fy }
            if (nb.id !== draggedNodeId) { nb.x! += fx; nb.y! += fy }
          }
        }
      }

      // Attraction
      simEdges.forEach(edge => {
        const source = currentNodes.find(n => n.id === edge.source)
        const target = currentNodes.find(n => n.id === edge.target)
        if (!source || !target) return

        const dx = target.x! - source.x!
        const dy = target.y! - source.y!
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        
        const force = (dist - 100) * 0.04
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force

        if (source.id !== draggedNodeId) { source.x! += fx; source.y! += fy }
        if (target.id !== draggedNodeId) { target.x! -= fx; target.y! -= fy }
      })

      // Gravity
      currentNodes.forEach(n => {
        if (n.id === draggedNodeId) return
        n.x! += (centerX - n.x!) * 0.015
        n.y! += (centerY - n.y!) * 0.015
      })

      setSimNodes([...currentNodes])
      setTicksCount(prev => prev + 1)
    }

    const timer = setInterval(tick, 1000 / 60)
    return () => clearInterval(timer)
  }, [simNodes, ticksCount, draggedNodeId])

  // Pan handlers
  const handleCanvasMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.target instanceof SVGElement && e.target.tagName === 'svg') {
      setIsDraggingCanvas(true)
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
    }
  }

  const handleCanvasMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isDraggingCanvas) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
    } else if (draggedNodeId) {
      const rect = e.currentTarget.getBoundingClientRect()
      const mouseX = (e.clientX - rect.left - pan.x) / zoom
      const mouseY = (e.clientY - rect.top - pan.y) / zoom
      const nodeIndex = simNodes.findIndex(n => n.id === draggedNodeId)
      if (nodeIndex !== -1) {
        const updated = [...simNodes]
        updated[nodeIndex].x = mouseX
        updated[nodeIndex].y = mouseY
        setSimNodes(updated)
      }
    }
  }

  const handleCanvasMouseUp = () => {
    setIsDraggingCanvas(false)
    setDraggedNodeId(null)
  }

  const handleNodeToggle = (nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
    setTicksCount(0) // restart simulation to settle changes
  }

  const findShortestPath = async () => {
    if (!pathSource || !pathTarget) return
    try {
      const res = await api.get(`/projects/${projectId}/knowledge-graph/path?source=${encodeURIComponent(pathSource)}&target=${encodeURIComponent(pathTarget)}`)
      setPathResult(res.data)
    } catch (err) {
      console.error(err)
    }
  }

  const getNodeColor = (type: string, isExpanded: boolean) => {
    if (type === 'repository') return '#06b6d4' // Cyan root
    if (type === 'subsystem') return '#d97706' // Amber subsystems
    if (type === 'capability') return '#ec4899' // Pink capabilities
    if (type === 'file') return '#38bdf8' // Sky file
    if (type === 'class') return '#a78bfa' // Purple class
    if (type === 'function' || type === 'method') return '#34d399' // Emerald functions
    if (type === 'route') return '#a75bfa' // Violet route
    if (type === 'model') return '#fb7185' // Rose models
    if (type === 'agent') return '#818cf8' // Indigo agents
    if (type === 'tool') return '#fbbf24' // Yellow tools
    return '#94a3b8'
  }

  return (
    <DashboardSection id="knowledge-graph" title="Knowledge Graph" icon={Cpu} accent="amber">
      <div className="glass-card min-h-[600px] flex flex-col">
        
        {/* Header / Filter Console */}
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-white/5 pb-4 mb-4 font-mono">
          <div>
            <p className="text-[10px] uppercase tracking-[0.22em] text-yowon-muted font-bold">Semantic Project Knowledge Graph</p>
            <h4 className="text-white text-xs mt-1">
              Double-click nodes to Expand/Collapse levels (drill down).
            </h4>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-yowon-muted" />
              <input
                type="text"
                placeholder="Search symbols..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-white/5 border border-white/10 rounded pl-8 pr-2.5 py-1 text-xs text-white focus:outline-none focus:border-amber-500/50 font-mono w-36"
              />
            </div>

            <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-lg p-0.5">
              <button onClick={() => setZoom(z => Math.min(2.0, z + 0.1))} className="p-1 text-yowon-muted hover:text-white rounded" title="Zoom In"><ZoomIn size={13} /></button>
              <button onClick={() => setZoom(z => Math.max(0.5, z - 0.1))} className="p-1 text-yowon-muted hover:text-white rounded" title="Zoom Out"><ZoomOut size={13} /></button>
              <button onClick={resetLayout} className="p-1 text-yowon-muted hover:text-white rounded" title="Reset Layout"><RefreshCw size={13} /></button>
            </div>
          </div>
        </div>

        {/* Pathfinder tracing block */}
        <div className="flex flex-wrap items-center gap-2.5 bg-white/[0.02] border border-white/5 rounded-xl p-3 mb-4 font-mono">
          <span className="text-[10px] text-yowon-muted uppercase font-bold">Shortest Dependency Path:</span>
          <input
            type="text"
            placeholder="Source (e.g. backend/main.py)"
            value={pathSource}
            onChange={(e) => setPathSource(e.target.value)}
            className="bg-white/5 border border-white/10 rounded px-2 py-0.5 text-xs text-white focus:outline-none focus:border-amber-500/50 font-mono w-40"
          />
          <span className="text-[10px] text-yowon-muted">➔</span>
          <input
            type="text"
            placeholder="Target (e.g. models)"
            value={pathTarget}
            onChange={(e) => setPathTarget(e.target.value)}
            className="bg-white/5 border border-white/10 rounded px-2 py-0.5 text-xs text-white focus:outline-none focus:border-amber-500/50 font-mono w-40"
          />
          <button
            onClick={findShortestPath}
            className="bg-amber-500 hover:bg-amber-600 text-black text-[10px] font-mono px-3 py-1 rounded font-bold transition-all"
          >
            Trace Path
          </button>
          {pathResult && (
            <button onClick={() => { setPathResult(null); setPathSource(''); setPathTarget('') }} className="text-[10px] text-red-400 hover:underline">Clear</button>
          )}
        </div>

        {/* Canvas SVG Grid */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* SVG Canvas Area (8 cols) */}
          <div className="lg:col-span-8 border border-white/5 bg-black/40 rounded-xl relative overflow-hidden min-h-[440px] select-none">
            <svg 
              className="w-full h-full min-h-[440px]" 
              onMouseDown={handleCanvasMouseDown}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onMouseLeave={handleCanvasMouseUp}
              style={{ cursor: isDraggingCanvas ? 'grabbing' : 'grab' }}
            >
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255, 255, 255, 0.15)" />
                </marker>
                <marker id="path-arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
                </marker>
              </defs>

              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Render Edges */}
                <g>
                  {simEdges.map((edge: Edge, idx: number) => {
                    const srcNode = simNodes.find(n => n.id === edge.source)
                    const tgtNode = simNodes.find(n => n.id === edge.target)
                    if (!srcNode || !tgtNode) return null

                    const isPathEdge = pathResult?.edges?.some(
                      (pe: any) => pe.source === edge.source && pe.target === edge.target
                    )

                    return (
                      <g key={`edge-${idx}`}>
                        <line
                          x1={srcNode.x!}
                          y1={srcNode.y!}
                          x2={tgtNode.x!}
                          y2={tgtNode.y!}
                          stroke={isPathEdge ? '#f59e0b' : 'rgba(255, 255, 255, 0.08)'}
                          strokeWidth={isPathEdge ? 2.5 : 1}
                          markerEnd={isPathEdge ? "url(#path-arrow)" : "url(#arrow)"}
                        />
                      </g>
                    )
                  })}
                </g>

                {/* Render Nodes */}
                <g>
                  {simNodes.map(node => {
                    const isSelected = selectedNode?.id === node.id
                    const isExpanded = expandedNodes.has(node.id)
                    const color = getNodeColor(node.type, isExpanded)
                    const radius = node.type === 'repository' ? 14 : (node.type === 'subsystem' ? 10 : 6)

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x!}, ${node.y!})`}
                        onClick={() => {
                          setSelectedNode(node)
                          if (onSelectNode) onSelectNode(node.label)
                        }}
                        onDoubleClick={() => handleNodeToggle(node.id)}
                        onMouseDown={e => {
                          e.stopPropagation()
                          setDraggedNodeId(node.id)
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          r={radius}
                          fill={color}
                          stroke={isSelected ? '#22d3ee' : (isExpanded ? '#fbbf24' : 'rgba(255,255,255,0.1)')}
                          strokeWidth={isSelected || isExpanded ? 2 : 1}
                        />
                        <text
                          y={radius + 12}
                          textAnchor="middle"
                          fill={isSelected ? '#22d3ee' : '#94a3b8'}
                          fontSize="8px"
                          fontFamily="monospace"
                          className="pointer-events-none select-none"
                        >
                          {node.label}
                        </text>
                      </g>
                    )
                  })}
                </g>
              </g>
            </svg>
            
          </div>
 
          {/* Right Side: Symbol Inspector (4 cols) */}
          <div className="lg:col-span-4 border border-white/5 bg-white/[0.01] rounded-xl p-4 flex flex-col font-mono text-xs overflow-y-auto max-h-[440px]">
            {selectedNode ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <span className="text-[9px] text-cyan-300 font-bold uppercase tracking-wider bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">
                    {selectedNode.type.toUpperCase()}
                  </span>
                  <button
                    onClick={() => handleNodeToggle(selectedNode.id)}
                    className="text-[9px] text-yowon-muted hover:text-white"
                  >
                    {expandedNodes.has(selectedNode.id) ? 'COLLAPSE NODE' : 'DRILL DOWN'}
                  </button>
                </div>
 
                <div>
                  <h4 className="text-white text-sm font-bold font-display">{selectedNode.label}</h4>
                  <p className="text-[10px] text-yowon-muted mt-0.5">ID: {selectedNode.id.split('::').pop()}</p>
                </div>
 
                <div className="space-y-3.5 pt-2 border-t border-white/5 leading-relaxed text-slate-300">
                  {selectedNode.metadata?.description && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">SEMANTIC DETAILS</span>
                      <p className="text-white/80 mt-1 text-[11px] font-sans">{selectedNode.metadata.description}</p>
                    </div>
                  )}

                  {selectedNode.metadata?.language && (
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <span className="text-yowon-muted text-[8px] block">LANGUAGE</span>
                        <span className="text-white font-bold block mt-0.5">{selectedNode.metadata.language}</span>
                      </div>
                      {selectedNode.metadata?.framework && (
                        <div>
                          <span className="text-yowon-muted text-[8px] block">FRAMEWORK</span>
                          <span className="text-white font-bold block mt-0.5">{selectedNode.metadata.framework}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {selectedNode.metadata?.layer && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">ARCHITECTURAL LAYER</span>
                      <span className="text-cyan-400 font-bold block mt-0.5">{selectedNode.metadata.layer.toUpperCase()}</span>
                    </div>
                  )}

                  {selectedNode.metadata?.base_classes && selectedNode.metadata.base_classes.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">INHERITS FROM</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {selectedNode.metadata.base_classes.map((cls: string) => (
                          <span key={cls} className="text-[9px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-slate-300">{cls}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedNode.metadata?.methods && selectedNode.metadata.methods.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">DECLARED METHODS ({selectedNode.metadata.methods.length})</span>
                      <div className="max-h-24 overflow-y-auto pr-1 space-y-1 mt-1 text-[9.5px]">
                        {selectedNode.metadata.methods.map((method: string) => (
                          <div key={method} className="text-emerald-400 font-bold font-mono">ƒ {method}()</div>
                        ))}
                      </div>
                    </div>
                  )}
 
                  {selectedNode.metadata?.file_path && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">DEFINED IN PATH</span>
                      <p className="bg-black/25 p-2 rounded border border-white/5 break-all text-[10px] font-mono mt-1">
                        {selectedNode.metadata.file_path}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center text-yowon-muted">
                <HelpCircle size={28} className="text-yowon-muted/30 mb-2" />
                <p className="text-xs">Select any node in the graph to inspect AST details.</p>
              </div>
            )}
          </div>
 
        </div>
      </div>
    </DashboardSection>
  )
}

export default function KnowledgeGraphPanel({ projectId, onSelectNode }: KnowledgeGraphPanelProps) {
  return (
    <ErrorBoundary name="Knowledge Graph Panel">
      <RepositoryIntelligenceWrapper projectId={projectId}>
        <KnowledgeGraphContent projectId={projectId} onSelectNode={onSelectNode} />
      </RepositoryIntelligenceWrapper>
    </ErrorBoundary>
  )
}

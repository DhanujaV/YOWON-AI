import React, { useState, useMemo, useEffect, useRef } from 'react'
import { 
  Cpu, Search, ZoomIn, ZoomOut, Link2, Lock, Unlock, 
  RefreshCw, Layers, ShieldAlert, GitCommit, GitPullRequest,
  Activity, Info, AlertTriangle, AlertCircle
} from 'lucide-react'
import { useDependencyGraph, useDependencyIntelligence } from './queries'
import { DashboardSection } from './DashboardSection'
import { GraphSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'
import { RepositoryIntelligenceWrapper } from './RepositoryIntelligenceWrapper'

interface DependencyGraphPanelProps {
  projectId: string
  onSelectNode?: (nodeName: string) => void
}

interface Node {
  id: string
  label: string
  type: string
  metadata?: {
    version?: string
    ecosystem?: string
    image?: string
    language?: string
    description?: string
  }
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface Edge {
  source: string
  target: string
  label: string
}

function DependencyGraphContent({ projectId, onSelectNode }: { projectId: string; onSelectNode?: (nodeName: string) => void }) {
  const { data: depGraph, isLoading, isError, error, refetch } = useDependencyGraph(projectId)
  const { data: depIntel } = useDependencyIntelligence(projectId)
  
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  
  // Layout states
  const [layoutMode, setLayoutMode] = useState<'force' | 'hierarchical'>('force')
  const [layoutLocked, setLayoutLocked] = useState(false)
  const [pinnedNodes, setPinnedNodes] = useState<Set<string>>(new Set())
  const [simTicks, setSimTicks] = useState(0)

  // Zoom / Pan state
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })

  // Force simulation state
  const [simNodes, setSimNodes] = useState<Node[]>([])
  const [simEdges, setSimEdges] = useState<Edge[]>([])
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)

  const graph = useMemo(() => {
    const data = depGraph?.success ? depGraph.data : depGraph
    return data || { nodes: [], edges: [] }
  }, [depGraph])

  const filteredGraph = useMemo(() => {
    if (!graph.nodes) return { nodes: [], edges: [] }
    const nodes: Node[] = graph.nodes
    const edges: Edge[] = graph.edges || []

    const filteredNodes = nodes.filter(n => {
      if (n.type === 'project' || n.type === 'ecosystem') return true
      return n.label.toLowerCase().includes(searchTerm.toLowerCase())
    })
    const nodeIds = new Set(filteredNodes.map(n => n.id))

    const filteredEdges = edges.filter(e => 
      nodeIds.has(e.source) && nodeIds.has(e.target)
    )

    return { nodes: filteredNodes, edges: filteredEdges }
  }, [graph, searchTerm])

  // Initialize and Reset Layout
  const resetLayout = () => {
    setSimTicks(0)
    setZoom(1.0)
    setPan({ x: 0, y: 0 })
    setPinnedNodes(new Set())
    setSelectedNode(null)
    
    if (filteredGraph.nodes.length === 0) return
    const centerX = 360
    const centerY = 240

    const initialNodes = filteredGraph.nodes.map(n => {
      const angle = Math.random() * 2 * Math.PI
      const r = n.type === 'project' ? 0 : (n.type === 'ecosystem' ? 100 : 200)
      return {
        ...n,
        x: centerX + r * Math.cos(angle) + (Math.random() - 0.5) * 20,
        y: centerY + r * Math.sin(angle) + (Math.random() - 0.5) * 20,
        vx: 0,
        vy: 0
      }
    })
    setSimNodes(initialNodes)
  }

  // Handle graph loading
  useEffect(() => {
    if (filteredGraph.nodes.length > 0) {
      resetLayout()
    }
  }, [filteredGraph])

  // Force Directed simulation loop
  useEffect(() => {
    if (simNodes.length === 0 || layoutLocked) return
    if (layoutMode === 'hierarchical') {
      // Arrange hierarchically
      const centerX = 360
      const nodes = [...simNodes]
      const projects = nodes.filter(n => n.type === 'project')
      const ecosystems = nodes.filter(n => n.type === 'ecosystem')
      const libraries = nodes.filter(n => n.type !== 'project' && n.type !== 'ecosystem')

      projects.forEach(n => { n.x = centerX; n.y = 50 })
      ecosystems.forEach((n, idx) => {
        const gap = 150
        n.x = centerX + (idx - (ecosystems.length - 1) / 2) * gap
        n.y = 180
      })
      libraries.forEach((n, idx) => {
        const columns = 5
        const row = Math.floor(idx / columns)
        const col = idx % columns
        n.x = centerX + (col - (columns - 1) / 2) * 110 + (row * 10)
        n.y = 320 + row * 80
      })
      setSimNodes(nodes)
      setSimEdges([...filteredGraph.edges])
      return
    }

    // Auto-stop simulation after 180 ticks to settle layouts
    if (simTicks > 180) {
      return
    }

    const centerX = 360
    const centerY = 240
    let currentNodes = [...simNodes]

    const tick = () => {
      // 1. Repulsion physics
      for (let i = 0; i < currentNodes.length; i++) {
        for (let j = i + 1; j < currentNodes.length; j++) {
          const na = currentNodes[i]
          const nb = currentNodes[j]
          const dx = nb.x! - na.x!
          const dy = nb.y! - na.y!
          const distSqr = dx * dx + dy * dy || 1
          const dist = Math.sqrt(distSqr)
          
          const minD = na.type === 'project' || nb.type === 'project' ? 180 : (na.type === 'ecosystem' || nb.type === 'ecosystem' ? 140 : 110)
          if (dist < minD) {
            const force = (minD - dist) * 0.35
            const fx = (dx / dist) * force
            const fy = (dy / dist) * force
            if (na.id !== draggedNodeId && !pinnedNodes.has(na.id)) { na.x! -= fx; na.y! -= fy }
            if (nb.id !== draggedNodeId && !pinnedNodes.has(nb.id)) { nb.x! += fx; nb.y! += fy }
          }
        }
      }

      // 2. Attraction along edges
      filteredGraph.edges.forEach(edge => {
        const source = currentNodes.find(n => n.id === edge.source)
        const target = currentNodes.find(n => n.id === edge.target)
        if (!source || !target) return

        const dx = target.x! - source.x!
        const dy = target.y! - source.y!
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        
        const targetLen = edge.label === 'uses' ? 150 : 200
        const k = 0.04
        const force = (dist - targetLen) * k
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force

        if (source.id !== draggedNodeId && !pinnedNodes.has(source.id)) { source.x! += fx; source.y! += fy }
        if (target.id !== draggedNodeId && !pinnedNodes.has(target.id)) { target.x! -= fx; target.y! -= fy }
      })

      // 3. Gravity center pulls
      const root = currentNodes.find(n => n.type === 'project')
      const targetX = root ? root.x! : centerX
      const targetY = root ? root.y! : centerY

      currentNodes.forEach(n => {
        if (n.id === draggedNodeId || pinnedNodes.has(n.id)) return
        n.x! += (targetX - n.x!) * 0.005
        n.y! += (targetY - n.y!) * 0.005
      })

      setSimNodes([...currentNodes])
      setSimEdges([...filteredGraph.edges])
      setSimTicks(prev => prev + 1)
    }

    const timer = setInterval(tick, 1000 / 60)
    return () => clearInterval(timer)
  }, [simNodes, simTicks, layoutLocked, layoutMode, draggedNodeId, pinnedNodes])

  // Pan handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.target instanceof SVGElement && e.target.tagName === 'svg') {
      setIsPanning(true)
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isPanning) {
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y })
    } else if (draggedNodeId) {
      const rect = e.currentTarget.getBoundingClientRect()
      const mouseX = (e.clientX - rect.left - pan.x) / zoom
      const mouseY = (e.clientY - rect.top - pan.y) / zoom
      const idx = simNodes.findIndex(n => n.id === draggedNodeId)
      if (idx !== -1) {
        const updated = [...simNodes]
        updated[idx].x = mouseX
        updated[idx].y = mouseY
        setSimNodes(updated)
      }
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
    setDraggedNodeId(null)
  }

  const togglePin = (nodeId: string) => {
    setPinnedNodes(prev => {
      const next = new Set(prev)
      if (next.has(nodeId)) next.delete(nodeId)
      else next.add(nodeId)
      return next
    })
  }

  const getNodeColor = (type: string, eco?: string) => {
    if (type === 'project') return '#06b6d4' // Cyan center
    if (type === 'ecosystem') return '#fbbf24' // Amber branch
    if (eco === 'Python') return '#3b82f6' // Python Blue
    if (eco === 'Node.js') return '#eab308' // Node Yellow
    if (eco === 'Docker') return '#10b981' // Docker Green
    return '#64748b'
  }

  // Compute metrics from intelligence DTO
  const circularDeps = (depIntel?.success ? depIntel.data?.circular_dependencies : depIntel?.circular_dependencies) || []
  const couplingMap = (depIntel?.success ? depIntel.data?.coupling : depIntel?.coupling) || {}
  const hotspots = (depIntel?.success ? depIntel.data?.hotspots : depIntel?.hotspots) || []

  return (
    <DashboardSection id="dependencies" title="Dependency Graph" icon={Cpu} accent="cyan">
      <div className="glass-card min-h-[580px] flex flex-col">
        
        {/* Header & Controls Console */}
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-white/5 pb-4 mb-4 font-mono">
          <div>
            <p className="text-[10px] uppercase tracking-[0.22em] text-yowon-muted font-bold">Dependency Tree & Manifest map</p>
            <p className="text-xs text-white mt-1">Stables layout with locking, pinning, and Ecosystem clustering.</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-yowon-muted" />
              <input
                type="text"
                placeholder="Search packages..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-white/5 border border-white/10 rounded pl-8 pr-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500/50 font-mono w-36"
              />
            </div>

            {/* Layout switch controls */}
            <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-lg p-0.5">
              <button
                onClick={() => setLayoutMode(l => l === 'force' ? 'hierarchical' : 'force')}
                className={`p-1.5 rounded text-yowon-muted hover:text-white ${layoutMode === 'hierarchical' ? 'bg-cyan-500/10 text-cyan-300' : ''}`}
                title="Toggle Hierarchical layout"
              >
                <Layers size={13} />
              </button>
              <button
                onClick={() => setLayoutLocked(l => !l)}
                className={`p-1.5 rounded text-yowon-muted hover:text-white ${layoutLocked ? 'bg-amber-500/10 text-amber-300' : ''}`}
                title={layoutLocked ? "Unlock layouts" : "Lock layouts"}
              >
                {layoutLocked ? <Lock size={13} /> : <Unlock size={13} />}
              </button>
              <button 
                onClick={resetLayout} 
                className="p-1.5 text-yowon-muted hover:text-white rounded"
                title="Recalculate layout"
              >
                <RefreshCw size={13} />
              </button>
            </div>

            {/* Zoom controls */}
            <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-lg p-0.5">
              <button onClick={() => setZoom(z => Math.min(2.0, z + 0.1))} className="p-1 text-yowon-muted hover:text-white rounded" title="Zoom In"><ZoomIn size={13} /></button>
              <button onClick={() => setZoom(z => Math.max(0.5, z - 0.1))} className="p-1 text-yowon-muted hover:text-white rounded" title="Zoom Out"><ZoomOut size={13} /></button>
            </div>
          </div>
        </div>

        {/* Graph Canvas & Inspector Grid */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* SVG Canvas Area (8 cols) */}
          <div className="lg:col-span-8 border border-white/5 bg-black/40 rounded-xl relative overflow-hidden min-h-[440px] select-none">
            <svg
              className="w-full h-full min-h-[440px]"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
            >
              <defs>
                <marker id="dep-arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.12)" />
                </marker>
              </defs>

              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Render Edges */}
                <g>
                  {simEdges.map((edge, idx) => {
                    const src = simNodes.find(n => n.id === edge.source)
                    const tgt = simNodes.find(n => n.id === edge.target)
                    if (!src || !tgt) return null
                    const isFrameworkEdge = edge.label === 'interprets' || edge.label === 'orchestrates'

                    return (
                      <g key={`edge-${idx}`}>
                        <line
                          x1={src.x!}
                          y1={src.y!}
                          x2={tgt.x!}
                          y2={tgt.y!}
                          stroke={isFrameworkEdge ? '#a78bfa' : 'rgba(255, 255, 255, 0.08)'}
                          strokeWidth={isFrameworkEdge ? 2.0 : 1.2}
                          strokeDasharray={isFrameworkEdge ? "4,4" : undefined}
                          markerEnd="url(#dep-arrow)"
                        />
                        {zoom >= 0.8 && (
                          <text
                            x={(src.x! + tgt.x!) / 2}
                            y={(src.y! + tgt.y!) / 2 - 4}
                            textAnchor="middle"
                            fill="rgba(255, 255, 255, 0.25)"
                            fontSize="7px"
                            fontFamily="monospace"
                          >
                            {edge.label}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </g>

                {/* Render Nodes */}
                <g>
                  {simNodes.map(node => {
                    const isSelected = selectedNode?.id === node.id
                    const isPinned = pinnedNodes.has(node.id)
                    const color = getNodeColor(node.type, node.metadata?.ecosystem)
                    const radius = node.type === 'project' ? 15 : (node.type === 'ecosystem' ? 10 : 7)

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x!}, ${node.y!})`}
                        onClick={() => {
                          setSelectedNode(node)
                          if (onSelectNode) onSelectNode(node.label)
                        }}
                        onDoubleClick={() => togglePin(node.id)}
                        onMouseDown={() => setDraggedNodeId(node.id)}
                        onMouseEnter={() => setHoveredNodeId(node.id)}
                        onMouseLeave={() => setHoveredNodeId(null)}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          r={radius}
                          fill={color}
                          stroke={isSelected ? '#22d3ee' : (isPinned ? '#fbbf24' : 'rgba(255,255,255,0.1)')}
                          strokeWidth={isSelected || isPinned ? 2 : 1}
                          className="transition-colors duration-250"
                        />
                        {isPinned && (
                          <circle r={2} fill="#000" />
                        )}
                        {(node.type === 'project' || node.type === 'ecosystem' || isSelected || hoveredNodeId === node.id || simNodes.length < 25 || zoom > 1.4) && (
                          <text
                            y={radius + 12}
                            textAnchor="middle"
                            fill={isSelected ? '#22d3ee' : (hoveredNodeId === node.id ? '#fff' : '#94a3b8')}
                            fontSize="9px"
                            fontFamily="monospace"
                            className="pointer-events-none select-none"
                          >
                            {node.label}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </g>
              </g>
            </svg>

            {/* Stabilization Status Bar Overlay */}
            <div className="absolute bottom-3 left-3 bg-black/60 border border-white/5 rounded-md px-2.5 py-1 text-[9px] font-mono text-yowon-muted flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${simTicks > 179 ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
              <span>{simTicks > 179 ? 'Physics Stabilized' : `Stabilizing (${simTicks}/180)`}</span>
            </div>
          </div>

          {/* Right Side: Dependency Intelligence Inspector (4 cols) */}
          <div className="lg:col-span-4 space-y-4 font-mono text-xs text-slate-300">
            {selectedNode ? (
              <div className="glass-card space-y-4 border border-cyan-500/10">
                <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-2">
                  <span className="text-[10px] text-cyan-300 font-bold uppercase">Package Inspector</span>
                  <button 
                    onClick={() => togglePin(selectedNode.id)}
                    className={`text-[9px] px-1.5 py-0.5 rounded border ${
                      pinnedNodes.has(selectedNode.id) 
                        ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' 
                        : 'bg-white/5 border-white/10 text-yowon-muted'
                    }`}
                  >
                    {pinnedNodes.has(selectedNode.id) ? 'PINNED' : 'DOUBLE CLICK TO PIN'}
                  </button>
                </div>

                <div>
                  <h4 className="text-white text-sm font-bold font-display">{selectedNode.label}</h4>
                  <p className="text-[10px] text-yowon-muted mt-0.5">Type: {selectedNode.type} &bull; Eco: {selectedNode.metadata?.ecosystem || 'Generic'}</p>
                </div>

                <div className="space-y-3 pt-2">
                  {selectedNode.metadata?.version && (
                    <div>
                      <span className="text-yowon-muted text-[9px] block">VERSION SPEC</span>
                      <span className="text-white font-bold block mt-0.5">{selectedNode.metadata.version}</span>
                    </div>
                  )}

                  {selectedNode.metadata?.description && (
                    <div>
                      <span className="text-yowon-muted text-[9px] block">MANIFEST DESCRIPTION</span>
                      <p className="text-slate-300 mt-1 leading-relaxed text-[11px] font-sans">{selectedNode.metadata.description}</p>
                    </div>
                  )}

                  {couplingMap[selectedNode.id] && (
                    <div className="grid grid-cols-2 gap-3 bg-white/[0.02] border border-white/5 rounded-lg p-2.5 text-center">
                      <div>
                        <span className="text-yowon-muted text-[8px] block">IN-DEGREE (CA)</span>
                        <span className="text-cyan-400 font-bold text-sm block mt-0.5">{couplingMap[selectedNode.id].ca}</span>
                      </div>
                      <div>
                        <span className="text-yowon-muted text-[8px] block">OUT-DEGREE (CE)</span>
                        <span className="text-amber-400 font-bold text-sm block mt-0.5">{couplingMap[selectedNode.id].ce}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {/* 1. Hotspots / Critical Chain items */}
                <div className="glass-card space-y-2">
                  <div className="flex items-center gap-1.5 text-white font-bold text-xs border-b border-white/5 pb-2">
                    <AlertCircle size={14} className="text-rose-400" />
                    <span>Circular Dependencies</span>
                  </div>
                  {circularDeps.length === 0 ? (
                    <p className="text-[10px] italic text-yowon-muted py-2">No circular reference loops detected.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {circularDeps.map((cycle: string[], idx: number) => (
                        <div key={idx} className="bg-red-500/5 border border-red-500/15 rounded p-2 text-[10px] space-y-1">
                          <span className="text-red-400 font-bold">CYCLE #{idx+1}</span>
                          <p className="text-yowon-muted font-sans font-mono truncate leading-normal">
                            {cycle.map(c => c.split('/').pop()).join(' ➔ ')}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 2. Hotspots list */}
                <div className="glass-card space-y-2">
                  <div className="flex items-center gap-1.5 text-white font-bold text-xs border-b border-white/5 pb-2">
                    <Activity size={14} className="text-amber-400" />
                    <span>Dependency Hotspots</span>
                  </div>
                  {hotspots.length === 0 ? (
                    <p className="text-[10px] italic text-yowon-muted py-2">No coupling hotspots detected.</p>
                  ) : (
                    <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                      {hotspots.map((h: string, idx: number) => (
                        <div key={idx} className="flex justify-between items-center bg-white/[0.02] border border-white/5 rounded p-2 text-[10px]">
                          <span className="text-slate-300 truncate max-w-[70%]">{h.split('/').pop()}</span>
                          <span className="text-amber-400 font-bold bg-amber-500/10 border border-amber-500/20 px-1 py-0.2 rounded">HIGH COUPLING</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    </DashboardSection>
  )
}

export default function DependencyGraphPanel({ projectId, onSelectNode }: DependencyGraphPanelProps) {
  return (
    <ErrorBoundary name="Dependency Graph Panel">
      <RepositoryIntelligenceWrapper projectId={projectId}>
        <DependencyGraphContent projectId={projectId} onSelectNode={onSelectNode} />
      </RepositoryIntelligenceWrapper>
    </ErrorBoundary>
  )
}

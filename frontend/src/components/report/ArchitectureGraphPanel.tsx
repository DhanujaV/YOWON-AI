import React, { useState, useMemo } from 'react'
import { Cpu, Layers, ZoomIn, ZoomOut, Heart, AlertTriangle, ShieldCheck, HelpCircle } from 'lucide-react'
import { useArchitectureGraph } from './queries'
import { DashboardSection } from './DashboardSection'
import { GraphSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'
import { RepositoryIntelligenceWrapper } from './RepositoryIntelligenceWrapper'

interface ArchitectureGraphPanelProps {
  projectId: string
  onSelectNode?: (nodeName: string) => void
}

interface Node {
  id: string
  label: string
  type: string
  metadata?: {
    description?: string
    technologies?: string[]
    files?: string[]
    // Rich v3 fields from architecture_engine
    purpose?: string
    responsibilities?: string[]
    inputs?: string
    outputs?: string
    consumers?: string[]
    providers?: string[]
    health?: number
    risk?: number
    complexity?: number
    confidence?: number
    summary?: string
    evidence?: string[]
    ownership?: string
  }
}

interface Edge {
  source: string
  target: string
  label: string
}


function ArchitectureGraphContent({ projectId, onSelectNode }: { projectId: string; onSelectNode?: (nodeName: string) => void }) {
  const { data: archGraph, isLoading, isError, error, refetch } = useArchitectureGraph(projectId)
  const [zoomScale, setZoomScale] = useState(1.0)
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })
  const [hoveredEdge, setHoveredEdge] = useState<Edge | null>(null)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

  const graph = useMemo(() => {
    const data = archGraph?.success ? archGraph.data : archGraph
    return data || { nodes: [], edges: [] }
  }, [archGraph])

  const nodes: Node[] = graph.nodes || []
  const edges: Edge[] = graph.edges || []

  // Dynamic topological layout
  const nodePositions = useMemo(() => {
    if (!nodes || nodes.length === 0) return {} as Record<string, { x: number; y: number }>

    const outgoing: Record<string, string[]> = {}
    const incoming: Record<string, number> = {}
    nodes.forEach(n => { outgoing[n.id] = []; incoming[n.id] = 0 })
    edges.forEach(e => {
      if (outgoing[e.source] !== undefined && incoming[e.target] !== undefined) {
        outgoing[e.source].push(e.target)
        incoming[e.target]++
      }
    })

    const layers: string[][] = []
    let queue = nodes.filter(n => incoming[n.id] === 0).map(n => n.id)
    const placed = new Set<string>()
    while (queue.length > 0) {
      layers.push(queue)
      queue.forEach(id => placed.add(id))
      const next: string[] = []
      queue.forEach(id => {
        outgoing[id]?.forEach(target => {
          incoming[target]--
          if (incoming[target] === 0 && !placed.has(target)) next.push(target)
        })
      })
      queue = next
    }
    const unplaced = nodes.filter(n => !placed.has(n.id))
    if (unplaced.length > 0) layers.push(unplaced.map(n => n.id))

    const CANVAS_W = 520
    const CANVAS_H = 440
    const colW = Math.min(130, CANVAS_W / Math.max(layers.length, 1))
    const positions: Record<string, { x: number; y: number }> = {}
    layers.forEach((layer, colIdx) => {
      const rowH = Math.min(100, CANVAS_H / Math.max(layer.length, 1))
      layer.forEach((nodeId, rowIdx) => {
        positions[nodeId] = {
          x: 70 + colIdx * colW,
          y: CANVAS_H / 2 - ((layer.length - 1) * rowH) / 2 + rowIdx * rowH
        }
      })
    })
    return positions
  }, [nodes, edges])

  // Canvas Pan handlers
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.target instanceof SVGElement && e.target.tagName === 'svg') {
      setIsPanning(true)
      setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isPanning) {
      setPanOffset({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      })
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
  }

  const getPosition = (id: string, index: number) => {
    if (nodePositions[id]) return nodePositions[id]
    return { x: 80 + (index % 3) * 160, y: 80 + Math.floor(index / 3) * 120 }
  }

  // Build inspector details purely from API node metadata — NO hardcoded registry
  const archDetails = useMemo(() => {
    if (!selectedNode) return null
    const m = selectedNode.metadata || {}
    return {
      purpose:          m.purpose || m.description || 'Architectural boundary subsystem layer.',
      responsibilities: Array.isArray(m.responsibilities) 
                          ? m.responsibilities 
                          : (typeof m.responsibilities === 'string' ? [m.responsibilities] : ['Executes layer business logic']),
      health:           m.health ?? 80.0,
      risk:             m.risk ?? 20.0,
      complexity:       m.complexity ?? 0,
      confidence:       m.confidence ?? 0.8,
      techs:            m.technologies || [],
      inputs:           m.inputs || 'Internal method parameters',
      outputs:          m.outputs || 'Data object return values',
      consumers:        Array.isArray(m.consumers) ? m.consumers : (m.consumers ? [m.consumers] : []),
      providers:        Array.isArray(m.providers) ? m.providers : (m.providers ? [m.providers] : []),
      summary:          m.summary || '',
      evidence:         m.evidence || [],
      ownership:        m.ownership || 'Engineering Team',
    }
  }, [selectedNode])

  if (isLoading) {
    return <GraphSkeleton />
  }

  if (isError) {
    return <PanelErrorFallback name="Architecture Graph" error={error} refetch={refetch} />
  }

  return (
    <DashboardSection id="architecture" title="Architecture Graph" icon={Layers} accent="cyan">
      <div className="glass-card min-h-[550px] flex flex-col">
        
        {/* Header & Zoom Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4 mb-4 font-mono">
          <div>
            <p className="text-[10px] uppercase tracking-[0.22em] text-yowon-muted font-bold">System Architecture Blueprint</p>
            <p className="text-xs text-white mt-1">Discover layers dynamically. Click layer nodes to trace components and inputs.</p>
          </div>
          
          <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-lg p-0.5">
            <button onClick={() => setZoomScale(s => Math.min(1.8, s + 0.1))} className="p-1.5 text-yowon-muted hover:text-white rounded" title="Zoom In"><ZoomIn size={12} /></button>
            <button onClick={() => setZoomScale(s => Math.max(0.5, s - 0.1))} className="p-1.5 text-yowon-muted hover:text-white rounded" title="Zoom Out"><ZoomOut size={12} /></button>
            <button onClick={() => { setZoomScale(1.0); setPanOffset({ x: 0, y: 0 }) }} className="px-2 py-0.5 text-[10px] text-yowon-muted hover:text-white rounded font-mono">Reset</button>
          </div>
        </div>

        {/* Workspace Canvas Grid */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* SVG Canvas Area (7 cols) */}
          <div className="lg:col-span-7 border border-white/5 bg-black/40 rounded-xl relative overflow-hidden min-h-[440px] select-none">
            <svg
              className="w-full h-full min-h-[440px]"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
            >
              <defs>
                <marker id="arch-arrow" viewBox="0 0 10 10" refX="28" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#06b6d4" />
                </marker>
              </defs>

              <g transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomScale})`}>
                {/* Edges */}
                <g>
                  {edges.map((edge, idx) => {
                    const srcNode = nodes.find(n => n.id === edge.source)
                    const tgtNode = nodes.find(n => n.id === edge.target)
                    if (!srcNode || !tgtNode) return null

                    const srcPos = getPosition(edge.source, idx)
                    const tgtPos = getPosition(edge.target, idx)

                    const dx = tgtPos.x - srcPos.x
                    const dy = tgtPos.y - srcPos.y
                    const cx1 = srcPos.x + dx * 0.4
                    const cy1 = srcPos.y
                    const cx2 = srcPos.x + dx * 0.6
                    const cy2 = tgtPos.y

                    const pathD = `M ${srcPos.x} ${srcPos.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${tgtPos.x} ${tgtPos.y}`
                    const isHovered = hoveredEdge === edge

                    return (
                      <g 
                        key={`edge-${idx}`}
                        onMouseEnter={() => setHoveredEdge(edge)}
                        onMouseLeave={() => setHoveredEdge(null)}
                      >
                        <path d={pathD} fill="none" stroke="transparent" strokeWidth={10} />
                        <path
                          d={pathD}
                          fill="none"
                          stroke={isHovered ? '#22d3ee' : 'rgba(6, 182, 212, 0.25)'}
                          strokeWidth={isHovered ? 2.5 : 1.5}
                          markerEnd="url(#arch-arrow)"
                        />
                      </g>
                    )
                  })}
                </g>

                {/* Nodes */}
                <g>
                  {nodes.map((node, idx) => {
                    const pos = getPosition(node.id, idx)
                    const width = 110
                    const height = 60
                    const isSelected = selectedNode?.id === node.id

                    return (
                      <g 
                        key={node.id} 
                        transform={`translate(${pos.x - width / 2}, ${pos.y - height / 2})`}
                        onClick={() => {
                          setSelectedNode(node)
                          if (onSelectNode) onSelectNode(node.label)
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <rect
                          width={width}
                          height={height}
                          rx={6}
                          fill="#06101D"
                          stroke={isSelected ? '#22d3ee' : 'rgba(6, 182, 212, 0.25)'}
                          strokeWidth={isSelected ? 2.5 : 1.5}
                        />
                        <rect width={3} height={height} rx={1} fill="#22d3ee" />
                        <text
                          x={10}
                          y={20}
                          fill="#22d3ee"
                          fontSize="8px"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          {node.label.toUpperCase()}
                        </text>
                        <text
                          x={10}
                          y={38}
                          fill="#94a3b8"
                          fontSize="6.5px"
                          fontFamily="monospace"
                        >
                          {node.metadata?.technologies?.[0] || 'Python'}
                        </text>
                      </g>
                    )
                  })}
                </g>
              </g>
            </svg>
          </div>

          {/* Right Side: Component Details Inspector (5 cols) */}
          <div className="lg:col-span-5 border border-white/5 bg-white/[0.01] rounded-xl p-4 flex flex-col font-mono text-xs overflow-y-auto max-h-[440px]">
            {selectedNode && archDetails ? (
              <div className="space-y-3.5">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <span className="text-[8px] text-cyan-300 font-bold uppercase tracking-wider bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">
                    {selectedNode.type.toUpperCase()}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-emerald-400">HEALTH {archDetails.health.toFixed(1)}%</span>
                    <span className="text-[9px] text-amber-400">RISK {archDetails.risk.toFixed(1)}%</span>
                  </div>
                </div>
                
                <h5 className="text-white font-bold text-sm">{selectedNode.label}</h5>
                <p className="text-[11px] text-slate-300 font-sans leading-relaxed">{archDetails.purpose}</p>

                {/* Health / Risk bars */}
                <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/5">
                  <div>
                    <div className="flex items-center gap-1.5 mb-1">
                      <Heart size={12} className="text-rose-400" />
                      <span className="text-yowon-muted text-[8px]">HEALTH</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full" style={{ width: `${archDetails.health}%` }} />
                    </div>
                    <span className="text-white font-bold text-[10px] mt-0.5 block">{archDetails.health.toFixed(1)}%</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5 mb-1">
                      <AlertTriangle size={12} className="text-amber-400" />
                      <span className="text-yowon-muted text-[8px]">RISK INDEX</span>
                    </div>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-amber-500 to-red-400 rounded-full" style={{ width: `${archDetails.risk}%` }} />
                    </div>
                    <span className="text-white font-bold text-[10px] mt-0.5 block">{archDetails.risk.toFixed(1)}/100</span>
                  </div>
                </div>

                <div className="space-y-2.5 pt-2 border-t border-white/5">
                  {/* Responsibilities */}
                  {archDetails.responsibilities.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">RESPONSIBILITIES</span>
                      <ul className="mt-1 space-y-0.5">
                        {archDetails.responsibilities.slice(0, 5).map((r: string, i: number) => (
                          <li key={i} className="text-slate-300 text-[10px] font-sans flex items-start gap-1">
                            <span className="text-cyan-400 mt-0.5">›</span>{r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Technologies */}
                  {archDetails.techs.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">TECHNOLOGIES</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {archDetails.techs.map((t: string, i: number) => (
                          <span key={i} className="text-[9px] bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-slate-300">{t}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-yowon-muted text-[8px] block">INPUT SIGNAL</span>
                      <span className="text-slate-400 block mt-0.5 text-[10px]">{archDetails.inputs}</span>
                    </div>
                    <div>
                      <span className="text-yowon-muted text-[8px] block">OUTPUT SIGNAL</span>
                      <span className="text-slate-400 block mt-0.5 text-[10px]">{archDetails.outputs}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-yowon-muted text-[8px] block">CONSUMED BY</span>
                      <span className="text-slate-400 block mt-0.5 text-[10px]">
                        {archDetails.consumers.join(', ') || '—'}
                      </span>
                    </div>
                    <div>
                      <span className="text-yowon-muted text-[8px] block">PROVIDED BY</span>
                      <span className="text-slate-400 block mt-0.5 text-[10px]">
                        {archDetails.providers.join(', ') || '—'}
                      </span>
                    </div>
                  </div>

                  {/* Ownership */}
                  <div>
                    <span className="text-yowon-muted text-[8px] block">OWNERSHIP</span>
                    <span className="text-slate-300 block mt-0.5 text-[10px]">{archDetails.ownership}</span>
                  </div>

                  {/* Confidence */}
                  <div>
                    <span className="text-yowon-muted text-[8px] block">DETECTION CONFIDENCE</span>
                    <span className="text-slate-300 block mt-0.5 text-[10px]">{Math.round(archDetails.confidence * 100)}%</span>
                  </div>

                  {/* Files */}
                  {selectedNode.metadata?.files && selectedNode.metadata.files.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">MAPPED SOURCE FILES ({selectedNode.metadata.files.length})</span>
                      <div className="max-h-20 overflow-y-auto pr-1 space-y-1 mt-1 text-[9.5px]">
                        {selectedNode.metadata.files.map((f: string) => (
                          <div key={f} className="text-cyan-400 truncate hover:underline cursor-pointer">{f.split('/').slice(-2).join('/')}</div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center text-yowon-muted">
                <HelpCircle size={28} className="text-yowon-muted/30 mb-2" />
                <p className="text-xs">Select any architecture layer to inspect health, risk, responsibilities, inputs, outputs, and source files.</p>
              </div>
            )}
          </div>

        </div>
      </div>
    </DashboardSection>
  )
}

export default function ArchitectureGraphPanel({ projectId, onSelectNode }: ArchitectureGraphPanelProps) {
  return (
    <ErrorBoundary name="Architecture Graph Panel">
      <RepositoryIntelligenceWrapper projectId={projectId}>
        <ArchitectureGraphContent projectId={projectId} onSelectNode={onSelectNode} />
      </RepositoryIntelligenceWrapper>
    </ErrorBoundary>
  )
}

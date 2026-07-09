import React, { useState, useMemo, useEffect } from 'react'
import { 
  Cpu, Search, ZoomIn, ZoomOut, Eye, EyeOff, Layers, 
  HelpCircle, ExternalLink, RefreshCw, Pin
} from 'lucide-react'
import { useTechnologyGraph } from './queries'
import { DashboardSection } from './DashboardSection'
import { GraphSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'
import { RepositoryIntelligenceWrapper } from './RepositoryIntelligenceWrapper'

interface TechnologyGraphPanelProps {
  projectId: string
  onSelectNode?: (nodeName: string) => void
}

interface NodeMetadata {
  confidence?: number
  category?: string
  version?: string
  description?: string
  detection_reason?: string
  sources?: string[]
  related_files?: string[]
  related_apis?: string[]
  related_services?: string[]
  related_databases?: string[]
  related_docker?: string[]
  related_agents?: string[]
  alternatives?: string[]
  runtime?: string
}

interface Node {
  id: string
  label: string
  type: string
  metadata?: NodeMetadata
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface Edge {
  source: string
  target: string
  label: string
  metadata?: { why?: string }
}



function TechnologyGraphContent({ projectId, onSelectNode }: { projectId: string; onSelectNode?: (nodeName: string) => void }) {
  const { data: techGraph, isLoading, isError, error, refetch } = useTechnologyGraph(projectId)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)
  
  // Controls
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string | null>(null)
  const [isolateMode, setIsolateMode] = useState(false)
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })

  // Simulation state
  const [simNodes, setSimNodes] = useState<Node[]>([])
  const [simEdges, setSimEdges] = useState<Edge[]>([])
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null)
  const [ticksCount, setTicksCount] = useState(0)

  const graph = useMemo(() => {
    const data = techGraph?.success ? techGraph.data : techGraph
    return data || { nodes: [], edges: [] }
  }, [techGraph])

  // Computed categories list
  const categoriesList = useMemo(() => {
    if (!graph.nodes) return []
    const cats = graph.nodes.map((n: any) => n.metadata?.category).filter(Boolean)
    return Array.from(new Set(cats)) as string[]
  }, [graph])

  const filteredGraph = useMemo(() => {
    if (!graph.nodes) return { nodes: [], edges: [] }
    const nodes: Node[] = graph.nodes
    const edges: Edge[] = graph.edges || []

    let resultNodes = nodes.filter(n => 
      n.label.toLowerCase().includes(searchTerm.toLowerCase())
    )

    if (activeCategoryFilter) {
      resultNodes = resultNodes.filter(n => n.metadata?.category === activeCategoryFilter)
    }

    if (isolateMode && selectedNode) {
      const neighbors = new Set<string>([selectedNode.id])
      edges.forEach(e => {
        if (e.source === selectedNode.id) neighbors.add(e.target)
        if (e.target === selectedNode.id) neighbors.add(e.source)
      })
      resultNodes = resultNodes.filter(n => neighbors.has(n.id))
    }

    const nodeIds = new Set(resultNodes.map(n => n.id))
    const resultEdges = edges.filter(e => 
      nodeIds.has(e.source) && nodeIds.has(e.target)
    )

    return { nodes: resultNodes, edges: resultEdges }
  }, [graph, searchTerm, activeCategoryFilter, isolateMode, selectedNode])

  // Initialize and Reset Layout
  const resetLayout = () => {
    setTicksCount(0)
    setZoom(1.0)
    setPan({ x: 0, y: 0 })
    setSelectedNode(null)
    setIsolateMode(false)
    
    if (filteredGraph.nodes.length === 0) return
    const centerX = 360
    const centerY = 240

    const initialNodes = filteredGraph.nodes.map(n => {
      const angle = Math.random() * 2 * Math.PI
      const r = 100 + Math.random() * 100
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

  useEffect(() => {
    if (filteredGraph.nodes.length > 0) {
      resetLayout()
    }
  }, [filteredGraph])

  // D3 force simulation loop
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
          
          if (dist < 90) {
            const force = (90 - dist) * 0.12
            const fx = (dx / dist) * force
            const fy = (dy / dist) * force
            if (na.id !== draggedNodeId) { na.x! -= fx; na.y! -= fy }
            if (nb.id !== draggedNodeId) { nb.x! += fx; nb.y! += fy }
          }
        }
      }

      // Attraction
      filteredGraph.edges.forEach(edge => {
        const source = currentNodes.find(n => n.id === edge.source)
        const target = currentNodes.find(n => n.id === edge.target)
        if (!source || !target) return

        const dx = target.x! - source.x!
        const dy = target.y! - source.y!
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        
        const force = (dist - 120) * 0.04
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
      setSimEdges([...filteredGraph.edges])
      setTicksCount(prev => prev + 1)
    }

    const timer = setInterval(tick, 1000 / 60)
    return () => clearInterval(timer)
  }, [simNodes, ticksCount, draggedNodeId])

  // Canvas Pan handlers
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

  const getCategoryColor = (cat?: string) => {
    const map: Record<string, string> = {
      LANGUAGE: '#38bdf8', // Sky
      FRAMEWORK: '#34d399', // Emerald
      LIBRARY: '#a78bfa', // Purple
      DATABASE: '#ec4899', // Pink
      PLATFORM: '#f59e0b', // Amber
      BUILD_TOOL: '#818cf8', // Indigo
      AI_INFRA: '#f87171' // Red
    }
    return map[cat || ''] || '#94a3b8'
  }

  // Build inspector details purely from API node metadata — NO hardcoded registry
  const techDetails = useMemo(() => {
    if (!selectedNode) return null
    const m = selectedNode.metadata || {}
    return {
      version:          m.version || 'Not specified',
      confidence:       m.confidence != null ? Math.round(m.confidence * 100) : null,
      category:         m.category || 'TECHNOLOGY',
      detection_reason: m.detection_reason || 'Detected via code analysis.',
      sources:          m.sources || [],
      description:      m.description || `${selectedNode.label} component detected in the codebase.`,
      related_files:    m.related_files || [],
      related_apis:     m.related_apis || [],
      related_services: m.related_services || [],
      related_agents:   m.related_agents || [],
      related_databases:m.related_databases || [],
      related_docker:   m.related_docker || [],
      alternatives:     m.alternatives || [],
      runtime:          m.runtime || 'Application Runtime',
    }
  }, [selectedNode])

  return (
    <DashboardSection id="technology" title="Technology Graph" icon={Cpu} accent="emerald">
      <div className="glass-card min-h-[580px] flex flex-col">
        
        {/* Header & Controls Console */}
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-white/5 pb-4 mb-4 font-mono">
          <div>
            <p className="text-[10px] uppercase tracking-[0.22em] text-yowon-muted font-bold">Stack Integration Topology</p>
            <p className="text-xs text-white mt-1">Select node to trace version, confidence, Docker, and alternate suggestions.</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-yowon-muted" />
              <input
                type="text"
                placeholder="Filter technology..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-white/5 border border-white/10 rounded pl-8 pr-2.5 py-1 text-xs text-white focus:outline-none focus:border-emerald-500/50 font-mono w-40"
              />
            </div>

            {/* Isolate trigger */}
            {selectedNode && (
              <button
                onClick={() => setIsolateMode(m => !m)}
                className={`flex items-center gap-1 text-[10px] px-2 py-1 rounded border transition-all ${
                  isolateMode 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
                    : 'bg-white/5 border-white/10 text-yowon-muted hover:text-white'
                }`}
              >
                {isolateMode ? <EyeOff size={11} /> : <Eye size={11} />}
                <span>ISOLATE</span>
              </button>
            )}

            {/* Reset */}
            <button 
              onClick={resetLayout} 
              className="p-1 text-yowon-muted hover:text-white rounded"
              title="Recalculate layout"
            >
              <RefreshCw size={13} />
            </button>

            {/* Zoom */}
            <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-lg p-0.5">
              <button onClick={() => setZoom(z => Math.min(2.0, z + 0.1))} className="p-1 text-yowon-muted hover:text-white rounded"><ZoomIn size={13} /></button>
              <button onClick={() => setZoom(z => Math.max(0.5, z - 0.1))} className="p-1 text-yowon-muted hover:text-white rounded"><ZoomOut size={13} /></button>
            </div>
          </div>
        </div>

        {/* Category filters row */}
        <div className="flex flex-wrap gap-1.5 mb-4 pb-2 border-b border-white/5 font-mono text-[9px]">
          <button
            onClick={() => setActiveCategoryFilter(null)}
            className={`px-2.5 py-1 rounded border transition-all ${!activeCategoryFilter ? 'bg-white/10 border-white/20 text-white' : 'bg-white/5 border-transparent text-yowon-muted hover:text-slate-300'}`}
          >
            ALL CATEGORIES
          </button>
          {categoriesList.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategoryFilter(cat)}
              className={`px-2.5 py-1 rounded border transition-all ${activeCategoryFilter === cat ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' : 'bg-white/5 border-transparent text-yowon-muted hover:text-slate-300'}`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Graph & Inspector Canvas Grid */}
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
                <marker id="tech-arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.15)" />
                </marker>
              </defs>

              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Edges */}
                <g>
                  {simEdges.map((edge, idx) => {
                    const src = simNodes.find(n => n.id === edge.source)
                    const tgt = simNodes.find(n => n.id === edge.target)
                    if (!src || !tgt) return null

                    return (
                      <g key={`edge-${idx}`}>
                        <line
                          x1={src.x!}
                          y1={src.y!}
                          x2={tgt.x!}
                          y2={tgt.y!}
                          stroke="rgba(255, 255, 255, 0.12)"
                          strokeWidth={1.5}
                          markerEnd="url(#tech-arrow)"
                        />
                        {zoom >= 0.8 && (
                          <text
                            x={(src.x! + tgt.x!) / 2}
                            y={(src.y! + tgt.y!) / 2 - 4}
                            textAnchor="middle"
                            fill="rgba(255, 255, 255, 0.35)"
                            fontSize="8px"
                            fontFamily="monospace"
                          >
                            {edge.label}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </g>

                {/* Nodes */}
                <g>
                  {simNodes.map(node => {
                    const isSelected = selectedNode?.id === node.id
                    const color = getCategoryColor(node.metadata?.category)
                    const radius = 10 + (node.metadata?.confidence || 1.0) * 12

                    return (
                      <g
                        key={node.id}
                        transform={`translate(${node.x!}, ${node.y!})`}
                        onClick={() => {
                          setSelectedNode(node)
                          if (onSelectNode) onSelectNode(node.label)
                        }}
                        onMouseDown={e => {
                          e.stopPropagation()
                          setDraggedNodeId(node.id)
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <circle
                          r={radius}
                          fill={color}
                          fillOpacity={0.15}
                          stroke={isSelected ? '#fff' : color}
                          strokeWidth={isSelected ? 2.5 : 1.5}
                        />
                        <circle
                          r={4}
                          fill={color}
                        />
                        <text
                          y={radius + 13}
                          textAnchor="middle"
                          fill={isSelected ? '#fff' : '#e4e4e7'}
                          fontSize="9px"
                          fontWeight="bold"
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

            {/* Bottom Legend */}
            <div className="absolute bottom-3 left-3 flex flex-wrap gap-x-3 gap-y-1 text-[8px] font-mono text-yowon-muted bg-black/60 p-2 rounded-lg border border-white/5">
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#38bdf8]" />Lang</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#34d399]" />Framework</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#a78bfa]" />Library</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#ec4899]" />DB</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#f59e0b]" />Platform</div>
              <div className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#f87171]" />AI</div>
            </div>
          </div>

          {/* Right Side: Technology Intelligence Inspector (5 cols) */}
          <div className="lg:col-span-5 border border-white/5 bg-white/[0.01] rounded-xl p-4 flex flex-col font-mono text-xs overflow-y-auto max-h-[440px]">
            {selectedNode && techDetails ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <span className="text-[8px] text-emerald-400 font-bold uppercase tracking-wider bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    {techDetails.category}
                  </span>
                  <span className="text-[10px] text-yowon-muted">
                    CONFIDENCE {techDetails.confidence !== null ? `${techDetails.confidence}%` : '—'}
                  </span>
                </div>
                
                <h5 className="text-white font-bold text-sm mt-1">{selectedNode.label}</h5>
                <span className="text-[10px] text-cyan-400 block">Version: {techDetails.version}</span>
                <span className="text-[10px] text-slate-400 block">{techDetails.runtime}</span>

                <div className="space-y-2.5 pt-2 border-t border-white/5">
                  
                  {/* Detection Reason */}
                  <div>
                    <span className="text-yowon-muted text-[8px] block">DETECTION REASON</span>
                    <span className="text-slate-300 block mt-0.5">{techDetails.detection_reason}</span>
                  </div>

                  {/* Source Manifests */}
                  {techDetails.sources.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">DETECTED IN MANIFESTS</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {techDetails.sources.map((s: string, i: number) => (
                          <span key={i} className="text-[9px] px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-slate-300">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related Files */}
                  {techDetails.related_files.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">FOUND IN {techDetails.related_files.length} FILE(S)</span>
                      <div className="max-h-24 overflow-y-auto mt-1 space-y-0.5">
                        {techDetails.related_files.slice(0, 12).map((f: string, i: number) => (
                          <p key={i} className="text-[9px] text-sky-300 font-mono truncate">{f.split('/').slice(-2).join('/')}</p>
                        ))}
                        {techDetails.related_files.length > 12 && (
                          <p className="text-[9px] text-yowon-muted">+{techDetails.related_files.length - 12} more files</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Related APIs */}
                  {techDetails.related_apis.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">RELATED APIs ({techDetails.related_apis.length})</span>
                      <div className="max-h-20 overflow-y-auto mt-1 space-y-0.5">
                        {techDetails.related_apis.slice(0, 8).map((a: string, i: number) => (
                          <p key={i} className="text-[9px] text-emerald-300 font-mono truncate">{a}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related Agents */}
                  {techDetails.related_agents.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">AI AGENTS USING THIS</span>
                      <div className="mt-1 space-y-0.5">
                        {techDetails.related_agents.slice(0, 5).map((a: string, i: number) => (
                          <p key={i} className="text-[9px] text-violet-300 font-mono">{a}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Docker */}
                  {techDetails.related_docker.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">DOCKER IMAGES / SERVICES</span>
                      <div className="mt-1 space-y-0.5">
                        {techDetails.related_docker.slice(0, 4).map((d: string, i: number) => (
                          <p key={i} className="text-[9px] text-emerald-400 font-mono">{d}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related Services */}
                  {techDetails.related_services.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">RELATED SERVICES ({techDetails.related_services.length})</span>
                      <div className="max-h-16 overflow-y-auto mt-1 space-y-0.5">
                        {techDetails.related_services.slice(0, 6).map((s: string, i: number) => (
                          <p key={i} className="text-[9px] text-amber-300 font-mono">{s}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Alternatives */}
                  {techDetails.alternatives.length > 0 && (
                    <div>
                      <span className="text-yowon-muted text-[8px] block">ALTERNATIVE TECHNOLOGIES</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {techDetails.alternatives.map((alt: string, i: number) => (
                          <span key={i} className="text-[9px] px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-slate-400 italic">{alt}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  <div>
                    <span className="text-yowon-muted text-[8px] block">DESCRIPTION</span>
                    <span className="text-slate-400 block mt-0.5 italic">{techDetails.description}</span>
                  </div>

                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-center text-yowon-muted">
                <HelpCircle size={28} className="text-yowon-muted/30 mb-2" />
                <p className="text-xs">Select any technology node in the graph to inspect full stack details.</p>
                <p className="text-[10px] mt-1 text-yowon-muted/60">Data includes version, confidence, detection reason, related files, APIs, agents, and alternatives.</p>
              </div>
            )}
          </div>

        </div>
      </div>
    </DashboardSection>
  )
}

export default function TechnologyGraphPanel({ projectId, onSelectNode }: TechnologyGraphPanelProps) {
  return (
    <ErrorBoundary name="Technology Graph Panel">
      <RepositoryIntelligenceWrapper projectId={projectId}>
        <TechnologyGraphContent projectId={projectId} onSelectNode={onSelectNode} />
      </RepositoryIntelligenceWrapper>
    </ErrorBoundary>
  )
}

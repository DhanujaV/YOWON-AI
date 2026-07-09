import React, { useState, useEffect, useRef, useMemo } from 'react'
import { 
  Folder, File, ChevronDown, ChevronRight, Download, FileText, 
  Code2, AlertCircle, Search, Compass, BarChart3, Activity, 
  HelpCircle, Eye, AlignLeft
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/api'
import { TreeSkeleton } from './Skeletons'
import { ErrorBoundary, PanelErrorFallback } from './ErrorBoundary'

interface RepositoryTreePanelProps {
  projectId: string
}

function TreeContent({ projectId }: { projectId: string }) {
  const [treeData, setTreeData] = useState<any[]>([])
  const [expandedPaths, setExpandedPaths] = useState<Record<string, boolean>>({})
  const [selectedFile, setSelectedFile] = useState<any>(null)
  const [loadingFile, setLoadingFile] = useState(false)
  const [searchInside, setSearchInside] = useState('')
  const [scrollTop, setScrollTop] = useState(0)
  
  const codeContainerRef = useRef<HTMLDivElement>(null)

  // Fetch root tree
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['repo-tree-root', projectId],
    queryFn: async () => {
      const res = await api.get(`/evaluations/${projectId}/repository-tree`)
      return res.data.data
    },
    enabled: !!projectId,
  })

  useEffect(() => {
    if (data) {
      setTreeData(data)
    }
  }, [data])

  const toggleFolder = async (path: string) => {
    const isExpanded = !!expandedPaths[path]
    setExpandedPaths(prev => ({ ...prev, [path]: !isExpanded }))

    if (!isExpanded) {
      try {
        const res = await api.get(`/evaluations/${projectId}/repository-tree?path=${encodeURIComponent(path)}`)
        if (res.data.success) {
          const children = res.data.data
          setTreeData(prev => {
            const updateNode = (nodes: any[]): any[] => {
              return nodes.map(node => {
                if (node.path === path) {
                  return { ...node, children }
                } else if (node.children) {
                  return { ...node, children: updateNode(node.children) }
                }
                return node
              })
            }
            return updateNode(prev)
          })
        }
      } catch (err) {
        console.error(err)
      }
    }
  }

  const loadFileContent = async (fpath: string) => {
    setLoadingFile(true)
    setScrollTop(0)
    if (codeContainerRef.current) {
      codeContainerRef.current.scrollTop = 0
    }
    try {
      const res = await api.get(`/evaluations/${projectId}/file/${encodeURIComponent(fpath)}`)
      if (res.data.success) {
        setSelectedFile(res.data.data)
      } else {
        setSelectedFile(res.data)
      }
    } catch {
      setSelectedFile({
        path: fpath,
        content: '// Unable to load file source content from repository cache.',
        symbols: [],
        metrics: {}
      })
    } finally {
      setLoadingFile(false)
    }
  }

  const handleDownload = () => {
    if (!selectedFile) return
    const blob = new Blob([selectedFile.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = selectedFile.path.split('/').pop() || 'file.txt'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Virtual Scrolling Calculations
  const LINE_HEIGHT = 18 // px
  const CONTAINER_HEIGHT = 380 // px
  
  const virtualData = useMemo(() => {
    if (!selectedFile || !selectedFile.content) return { lines: [], height: 0 }
    let rawLines = selectedFile.content.split('\n')
    
    // Apply search filter if inside-search is query
    if (searchInside) {
      rawLines = rawLines.map((line: string, idx: number) => {
        if (line.toLowerCase().includes(searchInside.toLowerCase())) {
          return { text: line, index: idx + 1, match: true }
        }
        return { text: line, index: idx + 1, match: false }
      })
    } else {
      rawLines = rawLines.map((line: string, idx: number) => ({ text: line, index: idx + 1, match: false }))
    }

    return {
      lines: rawLines,
      height: rawLines.length * LINE_HEIGHT
    }
  }, [selectedFile, searchInside])

  const visibleLines = useMemo(() => {
    if (virtualData.lines.length === 0) return []
    const startIdx = Math.max(0, Math.floor(scrollTop / LINE_HEIGHT) - 5)
    const endIdx = Math.min(virtualData.lines.length, startIdx + Math.ceil(CONTAINER_HEIGHT / LINE_HEIGHT) + 10)
    
    return virtualData.lines.slice(startIdx, endIdx).map((line: any, offsetIdx: number) => ({
      ...line,
      top: (startIdx + offsetIdx) * LINE_HEIGHT
    }))
  }, [virtualData, scrollTop])

  const jumpToLine = (lineNum: number) => {
    if (!codeContainerRef.current) return
    const targetScroll = (lineNum - 1) * LINE_HEIGHT
    codeContainerRef.current.scrollTop = targetScroll
    setScrollTop(targetScroll)
  }

  if (isLoading) {
    return <TreeSkeleton />
  }

  if (isError) {
    return <PanelErrorFallback name="Repository File System" error={error} refetch={refetch} />
  }

  const breadcrumbs = selectedFile?.path ? selectedFile.path.split('/') : []
  const fileIntel = selectedFile?.intelligence || {}

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      {/* Left Column: Repository Tree Explorer (4 cols) */}
      <div className="glass-card lg:col-span-4 max-h-[620px] overflow-y-auto flex flex-col border border-white/5">
        <div className="flex items-center justify-between pb-3 border-b border-white/5 mb-3 font-mono">
          <h3 className="text-[10px] uppercase tracking-[0.22em] text-yowon-muted">Repository Explorer</h3>
          <span className="text-[9px] text-cyan-300">WORKSPACE</span>
        </div>
        
        {treeData.length === 0 ? (
          <p className="text-xs text-yowon-muted py-12 text-center font-mono">Repository tree is empty.</p>
        ) : (
          <div className="space-y-0.5 font-mono text-xs text-slate-300 flex-1 overflow-y-auto pr-1">
            {(() => {
              const renderNode = (node: any, depth = 0): React.ReactNode => {
                const isDir = node.type === 'dir'
                const isExpanded = !!expandedPaths[node.path]
                const isActive = selectedFile?.path === node.path

                return (
                  <div key={node.path} className="select-none">
                    <div
                      className={`flex items-center gap-2.5 py-1.5 px-2.5 rounded transition-all cursor-pointer ${
                        isActive 
                          ? 'bg-cyan-500/10 text-cyan-300 font-bold border-l-2 border-cyan-400 pl-[1.5px]' 
                          : 'hover:bg-white/5 border-l-2 border-transparent'
                      }`}
                      style={{ paddingLeft: `${depth * 12 + 10}px` }}
                      onClick={() => isDir ? toggleFolder(node.path) : loadFileContent(node.path)}
                    >
                      {isDir ? (
                        <>
                          {isExpanded ? <ChevronDown size={13} className="text-slate-400 shrink-0" /> : <ChevronRight size={13} className="text-slate-400 shrink-0" />}
                          <Folder size={13.5} className="text-amber-400 fill-amber-400/10 shrink-0" />
                        </>
                      ) : (
                        <>
                          <span className="w-3.5 shrink-0" />
                          <File size={13.5} className="text-cyan-400 shrink-0" />
                        </>
                      )}
                      <span className="truncate text-[11px]">{node.name}</span>
                    </div>

                    {isDir && isExpanded && node.children && (
                      <div className="border-l border-white/[0.04] ml-[17px]">
                        {node.children.map((c: any) => renderNode(c, depth + 1))}
                      </div>
                    )}
                  </div>
                )
              }
              return treeData.map(node => renderNode(node))
            })()}
          </div>
        )}
      </div>

      {/* Middle & Right Column: Interactive Code Inspector & Intelligence (8 cols) */}
      <div className="lg:col-span-8 flex flex-col gap-5">
        {selectedFile ? (
          <div className="space-y-4 flex flex-col flex-1">
            
            {/* Breadcrumbs Row */}
            <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono text-yowon-muted bg-white/[0.02] border border-white/5 px-3 py-1.5 rounded-lg">
              <Compass size={12} className="text-cyan-300" />
              {breadcrumbs.map((b: string, i: number) => (
                <span key={i} className="flex items-center gap-1">
                  <span>{b}</span>
                  {i < breadcrumbs.length - 1 && <span>/</span>}
                </span>
              ))}
            </div>

            {/* Grid layout of Code + Outline/Intelligence */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
              
              {/* Virtual Code Viewer (8 cols) */}
              <div className="xl:col-span-8 glass-card p-0 border border-white/5 flex flex-col overflow-hidden min-h-[480px]">
                {/* Header */}
                <div className="bg-white/[0.03] border-b border-white/5 px-4 py-2 flex items-center justify-between text-yowon-muted font-mono text-[10px]">
                  <span className="flex items-center gap-1.5"><Code2 size={11} className="text-cyan-300" /> code_virtual_viewport</span>
                  <div className="relative">
                    <Search size={10} className="absolute left-2 top-1/2 -translate-y-1/2 text-yowon-muted" />
                    <input
                      type="text"
                      placeholder="Search inside file..."
                      value={searchInside}
                      onChange={e => setSearchInside(e.target.value)}
                      className="bg-black/40 border border-white/10 rounded pl-6 pr-2.5 py-0.5 text-[9px] text-white focus:outline-none focus:border-cyan-500/50 font-mono w-32"
                    />
                  </div>
                </div>

                {/* Virtual Scroll Area */}
                <div 
                  ref={codeContainerRef}
                  onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
                  className="flex-1 overflow-y-auto overflow-x-auto relative bg-[#040912]/80 font-mono text-[10.5px] min-h-[380px]"
                >
                  <div style={{ height: `${virtualData.height}px`, width: '100%', position: 'relative' }}>
                    {visibleLines.map((line: any) => (
                      <div 
                        key={line.index}
                        className={`absolute left-0 w-full flex items-center hover:bg-white/[0.02] pl-2 ${
                          line.match ? 'bg-cyan-500/10 border-l-2 border-cyan-400 pl-1.5' : ''
                        }`}
                        style={{ top: `${line.top}px`, height: `${LINE_HEIGHT}px` }}
                      >
                        <span className="w-9 text-slate-600 text-right select-none text-[8.5px] border-r border-white/5 pr-2 mr-3 font-mono">
                          {line.index}
                        </span>
                        <span className="text-slate-300 font-mono whitespace-pre select-text">
                          {line.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Sidebar Outline & File Intelligence (4 cols) */}
              <div className="xl:col-span-4 flex flex-col gap-4">
                
                {/* 1. File Intelligence summary card */}
                <div className="glass-card space-y-3.5 border border-white/5 p-4 text-[11px] font-sans">
                  <h4 className="text-white text-xs font-bold font-display border-b border-white/5 pb-2">File Intelligence</h4>
                  
                  <div className="space-y-3 leading-relaxed text-slate-300">
                    <div>
                      <span className="text-yowon-muted text-[8px] font-mono block">PURPOSE</span>
                      <p className="mt-0.5">{fileIntel.purpose || 'Implements service functionality.'}</p>
                    </div>

                    <div>
                      <span className="text-yowon-muted text-[8px] font-mono block">ARCHITECTURE LAYER</span>
                      <span className="text-cyan-400 font-bold block mt-0.5">{fileIntel.layer || 'Business Logic'}</span>
                    </div>

                    <div>
                      <span className="text-yowon-muted text-[8px] font-mono block">DB PERSISTENCE</span>
                      <span className="text-emerald-400 block mt-0.5">{fileIntel.db_usage || 'No database connections.'}</span>
                    </div>

                    <div>
                      <span className="text-yowon-muted text-[8px] font-mono block">AI ENGINE USAGE</span>
                      <span className="text-violet-300 font-bold block mt-0.5">{fileIntel.ai_usage || 'No AI model calls.'}</span>
                    </div>
                  </div>
                </div>

                {/* 2. Jump Outline symbols */}
                <div className="glass-card border border-white/5 p-4 flex flex-col max-h-[220px]">
                  <h4 className="text-white text-xs font-bold font-display border-b border-white/5 pb-2 flex items-center gap-1.5">
                    <AlignLeft size={13} className="text-amber-300" /> Symbol Outline
                  </h4>
                  <div className="flex-1 overflow-y-auto space-y-1 mt-2 font-mono text-[10px]">
                    {selectedFile.symbols && selectedFile.symbols.length > 0 ? (
                      selectedFile.symbols.map((sym: any, idx: number) => (
                        <div 
                          key={idx}
                          onClick={() => jumpToLine(sym.line_start)}
                          className="flex justify-between items-center py-1 hover:bg-white/5 px-1.5 rounded cursor-pointer text-slate-300 transition-colors"
                        >
                          <span className="truncate max-w-[70%] font-bold">{sym.name}</span>
                          <span className="text-cyan-400 shrink-0">L{sym.line_start}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-[10px] text-yowon-muted italic py-4 text-center">No class/function definitions found.</p>
                    )}
                  </div>
                </div>

              </div>

            </div>
          </div>
        ) : (
          <div className="glass-card flex-1 flex flex-col items-center justify-center py-28 text-center border border-white/5">
            <FileText size={36} className="text-yowon-muted/20 mb-3 animate-pulse" />
            <p className="text-xs text-yowon-muted font-mono max-w-sm leading-relaxed">
              Select any file from the folder tree on the left to activate virtual progressive code rendering and outline jump controls.
            </p>
          </div>
        )}
      </div>

    </div>
  )
}

export default function RepositoryTreePanel({ projectId }: RepositoryTreePanelProps) {
  return (
    <ErrorBoundary name="Repository Tree Explorer">
      <TreeContent projectId={projectId} />
    </ErrorBoundary>
  )
}

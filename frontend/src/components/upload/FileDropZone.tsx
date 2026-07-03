import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, X, FileText, Presentation, CheckCircle2 } from 'lucide-react'

interface FileDropZoneProps {
  accept: string
  label: string
  hint: string
  type: 'pdf' | 'ppt'
  file: File | null
  onFile: (file: File | null) => void
}

export default function FileDropZone({ accept, label, hint, type, file, onFile }: FileDropZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const Icon    = type === 'pdf' ? FileText : Presentation
  const color   = type === 'pdf' ? '#EF4444' : '#7C3AED'
  const bgColor = type === 'pdf' ? 'rgba(239,68,68,0.08)' : 'rgba(124,58,237,0.08)'

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) onFile(dropped)
  }, [onFile])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = e.target.files?.[0]
    if (picked) onFile(picked)
  }, [onFile])

  return (
    <div
      className={`relative rounded-xl border-2 border-dashed transition-all cursor-pointer overflow-hidden ${
        dragging
          ? 'border-cyan-300/60 bg-cyan-300/[0.06]'
          : file
            ? 'border-emerald-500/40 bg-emerald-500/[0.06]'
            : 'border-white/[0.10] hover:border-white/20 bg-white/[0.02] hover:bg-white/[0.04]'
      }`}
      onClick={() => inputRef.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()}
      aria-label={`Upload ${label}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={handleChange}
        tabIndex={-1}
      />

      <div className="p-5 text-center">
        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="file"
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <CheckCircle2 size={28} className="mx-auto mb-2 text-emerald-400" />
              <p className="text-xs font-semibold text-emerald-400 truncate px-2">{file.name}</p>
              <p className="text-[10px] text-yowon-muted mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <button
                type="button"
                onClick={e => { e.stopPropagation(); onFile(null) }}
                className="mt-3 flex items-center gap-1 mx-auto text-[10px] text-red-400/70 hover:text-red-400 transition"
              >
                <X size={11} /> Remove
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3 border"
                style={{ background: bgColor, borderColor: `${color}30` }}>
                <Icon size={22} style={{ color }} />
              </div>
              <p className="text-sm font-semibold text-white mb-1">{label}</p>
              <p className="text-[11px] text-yowon-muted mb-2">{hint}</p>
              <div className="flex items-center justify-center gap-1.5 text-[11px] text-yowon-muted">
                <Upload size={11} />
                <span>Drop here or click to browse</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

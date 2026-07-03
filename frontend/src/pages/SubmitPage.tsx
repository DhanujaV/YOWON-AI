import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Github, BarChart3, Zap, AlertCircle, FileStack, Sparkles,
  CheckCircle2, ClipboardCheck, Upload, FileText, ChevronRight,
  X, Eye,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import FileDropZone from '../components/upload/FileDropZone'
import { uploadProject, triggerEvaluation } from '../api/api'
import type { ProjectType } from '../types'

const PROJECT_TYPES: { value: ProjectType; emoji: string }[] = [
  { value: 'Auto Detect',         emoji: '🔍' },
  { value: 'Hackathon Project',   emoji: '⚡' },
  { value: 'University Project',  emoji: '🎓' },
  { value: 'Startup Pitch',       emoji: '🚀' },
  { value: 'Startup Product',     emoji: '💼' },
  { value: 'Research Project',    emoji: '🔬' },
  { value: 'Corporate Project',   emoji: '🏢' },
  { value: 'Enterprise System',   emoji: '⚙️' },
  { value: 'Open Source Project', emoji: '🌐' },
]

const STEPS = [
  { id: 1, label: 'Project Info',   icon: BarChart3 },
  { id: 2, label: 'Upload Assets',  icon: FileStack },
  { id: 3, label: 'Review',         icon: ClipboardCheck },
]

const UPLOAD_PHASES = [
  { label: 'Uploading project assets...', pct: 33 },
  { label: 'Triggering AI evaluation...', pct: 66 },
  { label: 'Entering mission control...',  pct: 95 },
]

export default function SubmitPage() {
  const navigate   = useNavigate()
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState<string | null>(null)
  const [uploadPhase, setUploadPhase] = useState(0)

  const [name,       setName]       = useState('')
  const [projectType, setProjectType] = useState<ProjectType>('Hackathon Project')
  const [githubUrl,   setGithubUrl]  = useState('')
  const [pdfFile,     setPdfFile]    = useState<File | null>(null)
  const [pptFile,     setPptFile]    = useState<File | null>(null)

  const activeStep =
    loading                                                    ? 3 :
    projectType && (githubUrl || pdfFile || pptFile) && name.trim() ? 3 :
    projectType && name.trim()                                 ? 2 :
    1

  const validate = (): string | null => {
    if (!name.trim()) return 'Project name is required'
    if (!githubUrl && !pdfFile && !pptFile) return 'Provide at least a GitHub URL or document'
    if (githubUrl && !/^https?:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/i.test(githubUrl.trim()))
      return 'GitHub URL must be a valid github.com repository URL'
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const err = validate()
    if (err) return setError(err)

    setLoading(true)
    setError(null)
    setUploadPhase(0)

    try {
      const { project_id } = await uploadProject({
        name: name.trim(),
        project_type: projectType,
        github_url: githubUrl || undefined,
        pdf_file: pdfFile || undefined,
        ppt_file: pptFile || undefined,
      })
      setUploadPhase(1)
      await triggerEvaluation(project_id)
      setUploadPhase(2)
      navigate(`/evaluate/${project_id}`)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      setError(axiosErr.response?.data?.detail || axiosErr.message || 'Upload failed')
      setUploadPhase(0)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell>
      <div className="fixed inset-0 pointer-events-none -z-[5] bg-aurora-radial opacity-80" />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-14 relative">

        {/* Page Header */}
        <motion.div
          className="text-center mb-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="inline-flex items-center gap-2 glass-pill px-3.5 py-1.5 mb-5 border-cyan-300/15">
            <Sparkles size={12} className="text-cyan-300" />
            <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-[0.22em]">
              Evaluation Intake
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mb-3 text-white"
            style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            Submit Your{' '}<span className="gradient-text">Project</span>
          </h1>
          <p className="text-yowon-muted max-w-md mx-auto text-sm leading-relaxed">
            Register project evidence for YOWON AI's judge-grade readiness evaluation.
          </p>
        </motion.div>

        {/* Step indicator */}
        <motion.div
          className="flex items-center justify-center gap-2 sm:gap-3 mb-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          {STEPS.map((step, i) => {
            const done   = activeStep > step.id
            const active = activeStep === step.id
            const Icon   = step.icon
            return (
              <div key={step.id} className="flex items-center gap-2 sm:gap-3">
                <div className="flex flex-col items-center gap-1.5">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold transition-all ${
                    done   ? 'form-step-done'    :
                    active ? 'form-step-active'  :
                             'form-step-pending'
                  }`}>
                    {done ? <CheckCircle2 size={16} /> : <Icon size={15} />}
                  </div>
                  <span className={`text-[10px] font-mono uppercase tracking-wider hidden sm:block ${
                    active ? 'text-cyan-300' : 'text-yowon-muted'
                  }`}>{step.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-8 sm:w-20 h-px mb-5 sm:mb-0 transition-all ${
                    done ? 'bg-gradient-to-r from-emerald-400/60 to-cyan-300/40' : 'bg-white/[0.08]'
                  }`} />
                )}
              </div>
            )
          })}
        </motion.div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">

          {/* Project Details */}
          <motion.div
            className="glass-card !p-6 accent-cyan"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/[0.03] to-transparent pointer-events-none rounded-[inherit]" />
            <div className="relative z-10">
              <div className="module-header">
                <div className="icon-wrap"><BarChart3 size={15} className="text-cyan-300" /></div>
                <div className="label-group">
                  <span className="eyebrow">Step 1</span>
                  <span className="title">Project Details</span>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-yowon-muted mb-2 uppercase tracking-wider">
                    Project Name <span className="text-cyan-300">*</span>
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    placeholder="e.g. MediAssist — AI-Powered Triage App"
                    className="yowon-input"
                    required
                  />
                </div>

                {/* Project type pill selector */}
                <div>
                  <label className="block text-xs font-semibold text-yowon-muted mb-2 uppercase tracking-wider">
                    Project Type <span className="text-cyan-300">*</span>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {PROJECT_TYPES.map(({ value, emoji }) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => setProjectType(value)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                          projectType === value
                            ? 'bg-cyan-300/12 border-cyan-300/35 text-cyan-200 shadow-[0_0_12px_rgba(0,229,255,0.12)]'
                            : 'bg-white/[0.03] border-white/[0.07] text-yowon-muted hover:border-white/12 hover:text-white'
                        }`}
                      >
                        <span>{emoji}</span>
                        {value}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Code & Links */}
          <motion.div
            className="glass-card !p-6"
            style={{ borderColor: 'rgba(52,211,153,0.18)' }}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/[0.03] to-transparent pointer-events-none rounded-[inherit]" />
            <div className="relative z-10">
              <div className="module-header">
                <div className="icon-wrap"><Github size={15} className="text-emerald-400" /></div>
                <div className="label-group">
                  <span className="eyebrow">Step 2a</span>
                  <span className="title">Code Repository</span>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-yowon-muted mb-2 uppercase tracking-wider">
                  GitHub Repository URL
                </label>
                <div className="relative">
                  <Github size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-yowon-muted" />
                  <input
                    type="url"
                    value={githubUrl}
                    onChange={e => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    className="yowon-input pl-10"
                  />
                  {githubUrl && (
                    <motion.div
                      initial={{ scale: 0 }} animate={{ scale: 1 }}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2"
                    >
                      {/^https?:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/i.test(githubUrl.trim())
                        ? <CheckCircle2 size={15} className="text-emerald-400" />
                        : <AlertCircle  size={15} className="text-amber-400" />
                      }
                    </motion.div>
                  )}
                </div>
                {githubUrl && (
                  <motion.p
                    initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                    className={`text-[11px] mt-1.5 font-medium ${
                      /^https?:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/i.test(githubUrl.trim())
                        ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {/^https?:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/i.test(githubUrl.trim())
                      ? '✓ Valid GitHub repository URL'
                      : '⚠ Enter a valid github.com/user/repo URL'
                    }
                  </motion.p>
                )}
              </div>
            </div>
          </motion.div>

          {/* Documents */}
          <motion.div
            className="glass-card !p-6 accent-violet"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <div className="absolute inset-0 bg-gradient-to-b from-violet-500/[0.03] to-transparent pointer-events-none rounded-[inherit]" />
            <div className="relative z-10">
              <div className="module-header">
                <div className="icon-wrap"><FileStack size={15} className="text-violet-400" /></div>
                <div className="label-group">
                  <span className="eyebrow">Step 2b</span>
                  <span className="title">Documents</span>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4">
                <FileDropZone
                  accept=".pdf"
                  label="PDF Presentation"
                  hint="PDF up to 50MB"
                  type="pdf"
                  file={pdfFile}
                  onFile={setPdfFile}
                />
                <FileDropZone
                  accept=".pptx,.ppt"
                  label="PowerPoint File"
                  hint="PPTX up to 50MB"
                  type="ppt"
                  file={pptFile}
                  onFile={setPptFile}
                />
              </div>
            </div>
          </motion.div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                className="flex items-start gap-3 rounded-xl px-4 py-3 text-sm"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.20)', color: '#F87171' }}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <span>{error}</span>
                <button type="button" onClick={() => setError(null)} className="ml-auto shrink-0">
                  <X size={14} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Upload Progress */}
          <AnimatePresence>
            {loading && (
              <motion.div
                className="glass-card !p-5 accent-violet"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
              >
                <div className="flex items-center justify-between text-xs font-mono text-yowon-muted mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full border-2 border-cyan-300/30 border-t-cyan-300 animate-spin" />
                    <span>{UPLOAD_PHASES[uploadPhase]?.label ?? 'Processing...'}</span>
                  </div>
                  <span className="text-cyan-300 font-bold">{UPLOAD_PHASES[uploadPhase]?.pct ?? 0}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-emerald-300 to-violet-500"
                    animate={{ width: `${UPLOAD_PHASES[uploadPhase]?.pct ?? 0}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <div className="flex justify-between mt-2">
                  {UPLOAD_PHASES.map((phase, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <div className={`w-1.5 h-1.5 rounded-full transition-all ${
                        i <= uploadPhase ? 'bg-cyan-300' : 'bg-white/15'
                      }`} />
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit */}
          <motion.button
            type="submit"
            disabled={loading}
            className="yowon-btn-primary w-full flex items-center justify-center gap-2 text-sm !py-3.5"
            whileHover={{ scale: loading ? 1 : 1.005 }}
            whileTap={{ scale: loading ? 1 : 0.995 }}
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Initializing AI Jury...
              </>
            ) : (
              <>
                <Zap size={16} />
                Evaluate Project
                <ChevronRight size={16} />
              </>
            )}
          </motion.button>

          <p className="text-center text-[11px] text-yowon-muted/70 font-mono">
            Encrypted intake · Parallel agent analysis · Verdict in minutes
          </p>
        </form>
      </main>
    </AppShell>
  )
}

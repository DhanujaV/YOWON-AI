import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Github, BarChart3, Zap, AlertCircle, FileStack, Sparkles,
  CheckCircle2, ClipboardCheck,
} from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import FileDropZone from '../components/upload/FileDropZone'
import { uploadProject, triggerEvaluation } from '../api/api'
import type { ProjectType } from '../types'

const PROJECT_TYPES: ProjectType[] = [
  'Auto Detect', 'University Project', 'Hackathon Project', 'Startup Pitch', 'Startup Product',
  'Research Project', 'Corporate Project', 'Enterprise System', 'Open Source Project',
]

const STEPS = [
  { id: 1, label: 'Project Information', icon: BarChart3 },
  { id: 2, label: 'Upload Assets', icon: FileStack },
  { id: 3, label: 'Evaluation Type', icon: Github },
  { id: 4, label: 'Review & Submit', icon: ClipboardCheck },
]

export default function SubmitPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploadPhase, setUploadPhase] = useState(0)

  const [name, setName] = useState('')
  const [projectType, setProjectType] = useState<ProjectType>('Hackathon Project')
  const [githubUrl, setGithubUrl] = useState('')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [pptFile, setPptFile] = useState<File | null>(null)

  const activeStep =
    loading ? 4 :
      projectType && (githubUrl || pdfFile || pptFile) && name.trim() ? 4 :
        projectType && name.trim() ? 3 :
          githubUrl || pdfFile || pptFile ? 2 :
            1

  const validate = (): string | null => {
    if (!name.trim()) return 'Project name is required'
    if (!githubUrl && !pdfFile && !pptFile) {
      return 'Provide at least a GitHub URL or document'
    }
    if (githubUrl && !/^https?:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/i.test(githubUrl.trim())) {
      return 'GitHub URL must be a valid github.com repository URL'
    }
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const validationError = validate()
    if (validationError) return setError(validationError)

    setLoading(true)
    setError(null)
    setUploadPhase(1)

    try {
      const { project_id } = await uploadProject({
        name: name.trim(),
        project_type: projectType,
        github_url: githubUrl || undefined,
        pdf_file: pdfFile || undefined,
        ppt_file: pptFile || undefined,
      })

      setUploadPhase(2)
      await triggerEvaluation(project_id)
      setUploadPhase(3)
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
      <div className="fixed inset-0 pointer-events-none -z-[5] bg-aurora-radial opacity-90" />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 sm:py-16 relative">
        <motion.div
          className="text-center mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="inline-flex items-center gap-2 glass-pill px-3 py-1.5 mb-4 border-cyan-300/20">
            <Sparkles size={12} className="text-cyan-300" />
            <span className="text-[10px] font-mono text-yowon-muted uppercase tracking-widest">
              Evaluation intake
            </span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-display font-bold mb-3">
            <span className="gradient-text">Evaluation Intake</span>
          </h1>
          <p className="text-yowon-muted max-w-md mx-auto">
            Register project evidence for YOWON AI&apos;s judge-grade readiness evaluation.
          </p>
        </motion.div>

        <motion.div
          className="flex items-center justify-center gap-2 sm:gap-4 mb-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          {STEPS.map((step, i) => {
            const done = activeStep > step.id
            const active = activeStep === step.id
            const Icon = step.icon
            return (
              <div key={step.id} className="flex items-center gap-2 sm:gap-4">
                <div className="flex flex-col items-center gap-1.5">
                  <div
                    className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-sm font-display font-semibold transition-all ${
                      done
                        ? 'form-step-done'
                        : active
                          ? 'form-step-active'
                          : 'form-step-pending'
                    }`}
                  >
                    {done ? <CheckCircle2 size={18} /> : <Icon size={16} />}
                  </div>
                  <span
                    className={`text-[10px] sm:text-xs font-mono uppercase tracking-wider hidden sm:block ${
                      active ? 'text-cyan-300' : 'text-yowon-muted'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`w-8 sm:w-16 h-px mb-5 sm:mb-0 ${
                      done ? 'bg-gradient-to-r from-emerald-300/70 to-cyan-300/50' : 'bg-yowon-border'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </motion.div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <motion.div
            className="glass-card space-y-5 border-l-2 border-l-cyan-300/60"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-cyan-300/10 flex items-center justify-center">
                <BarChart3 size={16} className="text-cyan-300" />
              </span>
              Project Details
            </h2>

            <div>
              <label className="block text-sm font-medium text-yowon-muted mb-2 font-display">
                Project Name <span className="text-cyan-300">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. MediAssist - AI-Powered Triage App"
                className="yowon-input"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-yowon-muted mb-2 font-display">
                Project Type <span className="text-cyan-300">*</span>
              </label>
              <select
                value={projectType}
                onChange={e => setProjectType(e.target.value as ProjectType)}
                className="yowon-input"
              >
                {PROJECT_TYPES.map(type => <option key={type} value={type}>{type}</option>)}
              </select>
            </div>

          </motion.div>

          <motion.div
            className="glass-card space-y-5 border-l-2 border-l-emerald-300/60"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-emerald-300/10 flex items-center justify-center">
                <Github size={16} className="text-emerald-300" />
              </span>
              Code & Links
            </h2>

            <div>
              <label className="block text-sm font-medium text-yowon-muted mb-2 font-display">
                GitHub Repository URL
              </label>
              <div className="relative">
                <Github size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-yowon-muted" />
                <input
                  type="url"
                  value={githubUrl}
                  onChange={e => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/username/repository"
                  className="yowon-input pl-9"
                />
              </div>
            </div>

          </motion.div>

          <motion.div
            className="glass-card space-y-5 border-l-2 border-l-violet-500/60"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center">
                <FileStack size={16} className="text-violet-300" />
              </span>
              Documents
            </h2>

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
          </motion.div>

          {error && (
            <motion.div
              className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <AlertCircle size={18} className="flex-shrink-0 mt-0.5" />
              {error}
            </motion.div>
          )}

          {loading && (
            <div className="glass-card p-4 border border-violet-500/20">
              <div className="flex justify-between text-xs font-mono text-yowon-muted mb-2">
                <span>
                  {uploadPhase === 1 ? 'Uploading project...' :
                   uploadPhase === 2 ? 'Triggering evaluation...' :
                   'Redirecting to live pipeline...'}
                </span>
                <span className="text-cyan-300">{uploadPhase * 33}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-yowon-border overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-cyan-300 via-emerald-300 to-violet-500"
                  animate={{ width: `${uploadPhase * 33}%` }}
                />
              </div>
            </div>
          )}

          <motion.button
            type="submit"
            disabled={loading}
            className="yowon-btn-primary w-full flex items-center justify-center gap-2 text-base"
            whileHover={{ scale: loading ? 1 : 1.01 }}
            whileTap={{ scale: loading ? 1 : 0.99 }}
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Initializing AI Jury...
              </>
            ) : (
              <>
                <Zap size={18} />
                Evaluate Project
              </>
            )}
          </motion.button>

          <p className="text-center text-xs text-yowon-muted/80 font-mono">
            Encrypted intake - Parallel agent analysis - Verdict in minutes
          </p>
        </form>
      </main>
    </AppShell>
  )
}

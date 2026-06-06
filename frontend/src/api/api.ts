import axios from 'axios'
import type { EvaluationProgress, ReportData, UploadProjectPayload } from '../types'
import { enrichReport } from '../utils/reportParser'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

export async function uploadProject(
  payload: UploadProjectPayload,
): Promise<{ project_id: string }> {
  const form = new FormData()
  form.append('name', payload.name)
  form.append('project_type', payload.project_type)
  if (payload.description) form.append('description', payload.description)
  if (payload.github_url) form.append('github_url', payload.github_url)
  if (payload.demo_video_url) form.append('demo_video_url', payload.demo_video_url)
  if (payload.pdf_file) form.append('pdf_file', payload.pdf_file)
  if (payload.ppt_file) form.append('ppt_file', payload.ppt_file)

  const res = await api.post('/upload-project', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function triggerEvaluation(projectId: string) {
  const res = await api.post(`/evaluate/${projectId}`)
  return res.data
}

export async function getStatus(
  projectId: string,
): Promise<{
  status: string
  evaluation_status?: string
  report_status?: string
  report_error?: string | null
  name: string
  project_type?: string
  project_id: string
  progress?: EvaluationProgress
}> {
  const res = await api.get(`/status/${projectId}`)
  return res.data
}

export function subscribeProgress(
  projectId: string,
  onMessage: (progress: EvaluationProgress) => void,
): EventSource {
  const es = new EventSource(`${API_BASE}/progress/${projectId}/stream`)
  es.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data) as EvaluationProgress)
    } catch {
      /* ignore malformed events */
    }
  }
  es.onerror = () => {
    /* browser will reconnect; poll backs up SSE */
  }
  return es
}

export async function getReport(projectId: string): Promise<ReportData> {
  const res = await api.get(`/report/${projectId}`, {
    validateStatus: s => s === 200 || s === 202,
  })
  if (res.status === 202) {
    const err = new Error(res.data?.message || 'Evaluation not complete yet')
    ;(err as Error & { code: string }).code = 'EVALUATION_INCOMPLETE'
    throw err
  }
  return enrichReport(res.data)
}

export function getPdfUrl(projectId: string): string {
  return `${API_BASE}/report/${projectId}/pdf`
}

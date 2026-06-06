export type VerdictType = 'ACCEPT' | 'IMPROVE' | 'REJECT'

export type AgentStatus = 'waiting' | 'running' | 'completed' | 'failed'

export type ProjectStatus = 'pending' | 'running' | 'done' | 'failed'

export type ReportStatus = 'pending' | 'ready' | 'failed' | 'skipped' | 'unknown'
export type ProjectType = 'University Project' | 'Hackathon Project' | 'Startup Pitch' | 'Research Project' | 'Corporate Project' | 'Open Source Project'



export interface Evaluation {

  score: number | null

  findings: string
  raw_score?: number | null

}



export interface AgentScores {

  technical?: number

  security?: number

  scalability?: number

  innovation?: number

  presentation?: number

  impact?: number

  engineering?: number

  innovation_scalability?: number

  ppt?: number

  risk_impact?: number

}



export interface VerdictData {

  overall_score?: number

  risk_level?: string

  verdict?: VerdictType

  blocking_issues?: string[]

  recommended_fixes?: string[]

  deployment_roadmap?: string[]

  agent_scores?: AgentScores
  raw_agent_scores?: AgentScores
  calibrated_agent_scores?: AgentScores
  agent_calibration_reasons?: Record<string, string[]>

  executive_summary?: string

  top_strengths?: string[]

  top_weaknesses?: string[]

  contradictions?: string[]
  project_type?: ProjectType | string
  evaluation_standard?: string
  scoring_weights?: Record<string, number>
  score_band?: string
  confidence?: number
  confidence_explanation?: string
  repository_statistics?: Record<string, number>
  repository_completeness_score?: number
  evidence_quality?: string
  penalties?: Array<{ factor: string; points?: number; dimension?: string }>
  calibration_adjustments?: Array<{ factor: string; points?: number; dimension?: string }>
  missing_evidence?: string[]
  positive_factors?: string[]

}



export interface ReportData {

  project_id: string

  project_name: string
  project_type?: ProjectType | string

  status: ProjectStatus

  evaluation_status?: string

  report_status?: ReportStatus

  report_error?: string | null

  overall_score: number | null

  verdict: VerdictType | string | null

  report_id: string | null

  evaluations: Record<string, Evaluation>

  verdict_data?: VerdictData
  raw_agent_scores?: AgentScores
  calibrated_agent_scores?: AgentScores

}



export interface UploadProjectPayload {

  name: string
  project_type: ProjectType

  description?: string

  github_url?: string

  demo_video_url?: string

  pdf_file?: File

  ppt_file?: File

}



export interface AgentStateEntry {

  status: AgentStatus | 'failed'

  started_at?: number | null

  ended_at?: number | null

  duration_sec?: number | null

  model?: string | null

  error?: string | null

}



export interface ProgressEvent {

  type: 'agent_start' | 'agent_complete'

  agent: string

  step?: number

  model?: string

  duration_sec?: number

  error?: string | null

  ts: number

}



export interface EvaluationProgress {

  step: number

  total: number

  agent: string

  current_task?: string

  status: 'running' | 'done' | 'failed' | 'unknown'

  evaluation_status?: string

  report_status?: ReportStatus

  report_error?: string | null

  elapsed_seconds?: number

  completion_percent?: number

  logs?: string[]

  agent_states?: Record<string, AgentStateEntry>

  events?: ProgressEvent[]

  project_id?: string

}



export interface PipelineAgent {

  id: string

  label: string

  desc: string

  icon: string

}



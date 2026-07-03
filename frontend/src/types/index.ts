export type VerdictType = 'ACCEPT' | 'IMPROVE' | 'REJECT'

export type AgentStatus = 'waiting' | 'running' | 'completed' | 'failed'

export type ProjectStatus = 'pending' | 'running' | 'done' | 'failed'

export type ReportStatus = 'pending' | 'ready' | 'failed' | 'skipped' | 'unknown'
export type ProjectType = 'Auto Detect' | 'University Project' | 'Hackathon Project' | 'Startup Pitch' | 'Startup Product' | 'Research Project' | 'Corporate Project' | 'Enterprise System' | 'Open Source Project'



export interface Evaluation {

  score: number | null

  findings: string

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
  forge?: number
  sentinel?: number
  visionary?: number
  showcase?: number
  guardian?: number

}

export interface RankingData {
  global_percentile?: number | null
  global_rank?: string
  category_percentile?: number | null
  category_rank?: string
  projects_compared?: number
  category_projects_compared?: number
}



export interface VerdictData {

  status?: 'INSUFFICIENT_EVIDENCE' | string

  final_reason?: string

  overall_score?: number

  risk_level?: string

  verdict?: VerdictType

  blocking_issues?: string[]

  recommended_fixes?: string[]

  roadmap?: string[] | string

  deployment_roadmap?: string[] | string

  agent_scores?: AgentScores

  executive_summary?: string

  top_strengths?: string[]

  top_weaknesses?: string[]

  contradictions?: string[]
  project_type?: ProjectType | string
  submitted_project_type?: ProjectType | string
  detected_project_type?: ProjectType | string
  detected_project_confidence?: number
  evaluation_standard?: string
  scoring_weights?: Record<string, number>
  score_band?: string
  confidence?: number
  confidence_explanation?: string
  confidence_sources?: string[]
  repository_statistics?: Record<string, number>
  repository_completeness_score?: number
  evidence_quality?: string
  penalties?: Array<{ factor: string; points?: number; dimension?: string }>
  missing_evidence?: string[]
  positive_factors?: string[]
  detected_technologies?: string[]
  detected_algorithms?: string[]
  architecture_summary?: string
  evidence_found?: string[]
  evidence_missing?: string[]
  calibration_explanation?: string
  project_type_justification?: string
  community_impact_score?: number
  ranking?: RankingData

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
  evaluation_id?: string
  evaluations: Record<string, Evaluation>
  verdict_data?: VerdictData
}



export interface UploadProjectPayload {

  name: string
  project_type: ProjectType

  github_url?: string

  pdf_file?: File

  ppt_file?: File

}



export interface AgentStateEntry {

  status: AgentStatus | 'failed'
  label?: string | null

  started_at?: number | null

  ended_at?: number | null

  duration_sec?: number | null

  model?: string | null

  error?: string | null

}



export interface ProgressEvent {

  type: 'agent_start' | 'agent_complete'

  agent: string
  label?: string

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



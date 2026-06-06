import type { Evaluation, ReportData, VerdictData } from '../types'

function extractJson(text: string): VerdictData | null {
  const fenced = text.match(/```json\s*([\s\S]*?)\s*```/)
  if (fenced) {
    try {
      return JSON.parse(fenced[1]) as VerdictData
    } catch {
      /* continue */
    }
  }

  const brace = text.match(/\{[\s\S]*\}/)
  if (brace) {
    try {
      return JSON.parse(brace[0]) as VerdictData
    } catch {
      /* continue */
    }
  }

  return null
}

function extractBullets(text: string, keywords: string[]): string[] {
  const lines = text.split('\n')
  const items: string[] = []
  let capturing = false

  for (const line of lines) {
    const lower = line.toLowerCase()
    if (keywords.some(k => lower.includes(k))) {
      capturing = true
      const inline = line.replace(/^[-*#\s]+/, '').replace(/.*:/, '').trim()
      if (inline.length > 10) items.push(inline)
      continue
    }
    if (capturing) {
      const bullet = line.match(/^\s*[-*•]\s+(.+)/)
      if (bullet) {
        items.push(bullet[1].trim())
      } else if (line.trim() === '' || /^[A-Z][A-Z\s]+:/.test(line)) {
        if (items.length > 0) break
        capturing = false
      }
    }
  }

  return items.slice(0, 6)
}

function extractSummary(text: string): string {
  const summaryMatch = text.match(
    /(?:executive summary|project summary|summary)[:\s]*\n?([\s\S]{40,600}?)(?:\n\n|\n[A-Z][A-Z]|\n[-*]|$)/i,
  )
  if (summaryMatch) return summaryMatch[1].trim()

  const paragraphs = text
    .split('\n\n')
    .map(p => p.trim())
    .filter(p => p.length > 60 && !p.startsWith('{'))
  return paragraphs[0]?.slice(0, 500) ?? 'Multi-agent evaluation complete. Review detailed findings below.'
}

function deriveStrengths(evaluations: Record<string, Evaluation>): string[] {
  const strengths: string[] = []
  for (const [key, ev] of Object.entries(evaluations)) {
    if (ev.score !== null && ev.score >= 75) {
      strengths.push(`Strong ${key.replace(/_/g, ' ')} performance (${Math.round(ev.score)}/100)`)
    }
    const found = extractBullets(ev.findings, ['strength', 'positive', 'strong', 'excellent'])
    strengths.push(...found)
  }
  return [...new Set(strengths)].slice(0, 5)
}

function deriveWeaknesses(evaluations: Record<string, Evaluation>): string[] {
  const weaknesses: string[] = []
  for (const [key, ev] of Object.entries(evaluations)) {
    if (ev.score !== null && ev.score < 60) {
      weaknesses.push(`Weak ${key.replace(/_/g, ' ')} score (${Math.round(ev.score)}/100)`)
    }
    const found = extractBullets(ev.findings, ['weakness', 'concern', 'risk', 'issue', 'gap', 'missing'])
    weaknesses.push(...found)
  }
  return [...new Set(weaknesses)].slice(0, 5)
}

export function enrichReport(raw: ReportData): ReportData {
  const chief = raw.evaluations?.chief_evaluation
  const parsed = raw.verdict_data
    ? (raw.verdict_data as VerdictData)
    : chief?.findings
      ? extractJson(chief.findings)
      : null

  const agentScores = buildAgentScores(parsed, raw.evaluations)

  const verdict_data: VerdictData = {
    ...parsed,
    overall_score: parsed?.overall_score ?? raw.overall_score ?? 0,
    risk_level: parsed?.risk_level ?? inferRiskLevel(raw.overall_score),
    verdict: (parsed?.verdict ?? raw.verdict) as VerdictData['verdict'],
    blocking_issues:
      parsed?.blocking_issues?.length
        ? parsed.blocking_issues
        : extractBullets(chief?.findings ?? '', ['blocking', 'critical', 'must fix']),
    recommended_fixes:
      parsed?.recommended_fixes?.length
        ? parsed.recommended_fixes
        : extractBullets(chief?.findings ?? '', ['recommend', 'fix', 'improve', 'action']),
    deployment_roadmap:
      parsed?.deployment_roadmap?.length
        ? parsed.deployment_roadmap
        : extractBullets(chief?.findings ?? '', ['roadmap', 'deploy', 'phase', 'next step']),
    agent_scores: agentScores,
    executive_summary: parsed?.executive_summary ?? extractSummary(chief?.findings ?? ''),
    top_strengths: parsed?.top_strengths?.length
      ? parsed.top_strengths
      : deriveStrengths(raw.evaluations),
    top_weaknesses: parsed?.top_weaknesses?.length
      ? parsed.top_weaknesses
      : deriveWeaknesses(raw.evaluations),
    contradictions: parsed?.contradictions ?? [],
    project_type: parsed?.project_type ?? raw.project_type,
    evaluation_standard: parsed?.evaluation_standard,
    scoring_weights: parsed?.scoring_weights ?? {},
    score_band: parsed?.score_band,
    confidence: parsed?.confidence ?? 0,
    penalties: parsed?.penalties ?? [],
    missing_evidence: parsed?.missing_evidence ?? [],
    positive_factors: parsed?.positive_factors ?? [],
  }

  return { ...raw, verdict_data }
}

function inferRiskLevel(score: number | null): string {
  if (score === null) return 'MEDIUM'
  if (score >= 80) return 'LOW'
  if (score >= 50) return 'MEDIUM'
  return 'HIGH'
}

function buildAgentScores(
  parsed: VerdictData | null,
  evaluations: Record<string, Evaluation>,
): VerdictData['agent_scores'] {
  if (parsed?.agent_scores) {
    return ensureAllDimensions(parsed.agent_scores, evaluations)
  }

  const scores: Record<string, number> = {}
  for (const [key, ev] of Object.entries(evaluations)) {
    if (ev.score !== null && ev.score !== undefined) {
      scores[key] = ev.score
    }
  }

  const technical = scores.technical ?? scores.engineering
  const security = scores.security
  const innovation = scores.innovation ?? scores.innovation_scalability
  const presentation = scores.presentation ?? scores.ppt
  const impact = scores.impact ?? scores.risk ?? scores.risk_impact
  const scalability = scores.scalability

  return {
    technical,
    security,
    scalability,
    innovation,
    presentation,
    impact,
    engineering: technical,
    innovation_scalability: innovation,
    ppt: presentation,
    risk_impact: impact,
  }
}

function ensureAllDimensions(
  agentScores: NonNullable<VerdictData['agent_scores']>,
  evaluations: Record<string, Evaluation>,
): VerdictData['agent_scores'] {
  const result = { ...agentScores }
  const keys = ['technical', 'security', 'scalability', 'innovation', 'presentation', 'impact'] as const
  for (const key of keys) {
    if (result[key] == null) {
      const evKey = key === 'impact' ? 'risk' : key
      const ev = evaluations[evKey]
      if (ev?.score != null) result[key] = ev.score
    }
  }
  return result
}

export function getRadarData(agentScores: VerdictData['agent_scores']) {
  if (!agentScores) return []
  const map = [
    { key: 'technical', label: 'Technical' },
    { key: 'security', label: 'Security' },
    { key: 'scalability', label: 'Scalability' },
    { key: 'innovation', label: 'Innovation' },
    { key: 'presentation', label: 'Presentation' },
    { key: 'impact', label: 'Impact' },
  ]
  return map
    .filter(m => agentScores[m.key as keyof typeof agentScores] != null)
    .map(m => ({
      subject: m.label,
      score: agentScores[m.key as keyof typeof agentScores] as number,
      fullMark: 100,
    }))
}

export function computeConsensus(agentScores: VerdictData['agent_scores']): number {
  if (!agentScores) return 0
  const values = [
    agentScores.technical,
    agentScores.security,
    agentScores.scalability,
    agentScores.innovation,
    agentScores.presentation,
    agentScores.impact,
  ].filter((v): v is number => v != null && v > 0)

  if (values.length < 2) return 0

  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length
  const stdDev = Math.sqrt(variance)
  return Math.max(40, Math.min(99, Math.round(100 - stdDev * 2.2)))
}

export function scoreColor(score: number): string {
  if (score >= 80) return '#10B981'
  if (score >= 50) return '#F59E0B'
  return '#EF4444'
}

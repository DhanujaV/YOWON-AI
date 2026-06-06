import type { ReportData } from '../types'
import { enrichReport } from './reportParser'

const DEMO_RAW: ReportData = {
  project_id: 'demo-sentinel-001',
  project_name: 'NeuralOps Command Center',
  status: 'done',
  overall_score: 82,
  verdict: 'ACCEPT',
  report_id: 'demo-report',
  evaluations: {
    engineering: {
      score: 85,
      findings:
        'STRENGTHS:\n- Clean microservices architecture with proper separation\n- Comprehensive test coverage at 78%\n- Well-documented API contracts\n\nCONCERNS:\n- Missing circuit breaker patterns on external calls',
    },
    innovation_scalability: {
      score: 80,
      findings:
        'INNOVATION:\n- Novel multi-agent orchestration approach\n- Real-time evaluation pipeline\n\nSCALABILITY:\n- Horizontal scaling ready with stateless workers\n- Redis caching layer recommended for 10K+ concurrent users',
    },
    ppt: {
      score: 88,
      findings:
        'PRESENTATION QUALITY:\n- Clear problem statement and market sizing\n- Strong demo narrative with live metrics\n- Professional visual design throughout deck',
    },
    risk_impact: {
      score: 76,
      findings:
        'IMPACT ANALYSIS:\n- Addresses critical deployment readiness gap\n- Enterprise security teams as primary buyers\n\nRISK FACTORS:\n- Dependency on third-party LLM availability\n- Data residency requirements for EU clients',
    },
    chief_evaluation: {
      score: 82,
      findings: JSON.stringify({
        overall_score: 82,
        risk_level: 'LOW',
        verdict: 'ACCEPT',
        blocking_issues: ['Configure production secrets management before deploy'],
        recommended_fixes: [
          'Add health check endpoints for all services',
          'Implement request rate limiting on upload endpoint',
          'Set up distributed tracing with OpenTelemetry',
        ],
        deployment_roadmap: [
          'Phase 1: Staging deployment with synthetic load tests',
          'Phase 2: Security penetration test and remediation',
          'Phase 3: Canary release to 5% production traffic',
          'Phase 4: Full production rollout with monitoring',
        ],
        agent_scores: {
          technical: 85,
          security: 78,
          scalability: 80,
          innovation: 82,
          presentation: 88,
          impact: 76,
        },
      }),
    },
  },
}

export function getDemoReport(): ReportData {
  return enrichReport(DEMO_RAW)
}

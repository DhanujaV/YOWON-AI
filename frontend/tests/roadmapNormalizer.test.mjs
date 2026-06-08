import { normalizeDisplayList, phaseDeploymentRoadmap } from '../src/utils/listNormalizer.ts'
import { enrichReport } from '../src/utils/reportParser.ts'

const roadmap = normalizeDisplayList('Phase 1\n- Improve test coverage\n- Add authentication\nPhase 2\n- Harden security')

if (roadmap.length !== 5) {
  throw new Error(`Expected 5 roadmap lines, got ${roadmap.length}`)
}

if (roadmap[0] !== 'Phase 1' || roadmap[1] !== 'Improve test coverage' || roadmap[2] !== 'Add authentication') {
  throw new Error(`Roadmap normalization failed: ${JSON.stringify(roadmap)}`)
}

if (roadmap.some(item => item.length === 1)) {
  throw new Error(`Roadmap was split into single characters: ${JSON.stringify(roadmap)}`)
}

const phases = phaseDeploymentRoadmap([
  'Add automated tests',
  'Improve documentation',
  'Add CI/CD pipeline',
  'Strengthen security controls',
])

if (phases.length !== 3) {
  throw new Error(`Expected 3 phases, got ${phases.length}`)
}

if (phases[0].title !== 'Phase 1' || phases[0].items.length !== 2) {
  throw new Error(`Phase 1 grouping failed: ${JSON.stringify(phases)}`)
}

if (phases[1].items[0] !== 'Add CI/CD pipeline' || phases[2].items[0] !== 'Strengthen security controls') {
  throw new Error(`Phase grouping order failed: ${JSON.stringify(phases)}`)
}

const enriched = enrichReport({
  project_id: 'p1',
  project_name: 'Demo',
  status: 'done',
  overall_score: 70,
  verdict: 'IMPROVE',
  report_id: 'r1',
  evaluations: {
    chief_evaluation: {
      score: 70,
      findings: 'Final Verdict',
    },
  },
  verdict_data: {
    overall_score: 70,
    verdict: 'IMPROVE',
    risk_level: 'MEDIUM',
    deployment_roadmap: 'Add automated tests\nImprove documentation\nAdd CI/CD pipeline\nStrengthen security controls',
  },
})

if (!Array.isArray(enriched.verdict_data?.deployment_roadmap)) {
  throw new Error('Parser did not normalize deployment_roadmap to an array')
}

if (enriched.verdict_data.deployment_roadmap.some(item => item.length === 1)) {
  throw new Error(`Parser produced character roadmap items: ${JSON.stringify(enriched.verdict_data.deployment_roadmap)}`)
}

const characterRoadmap = normalizeDisplayList(['P', 'h', 'a', 's', 'e', ' ', '1', '\n', '-', ' ', 'A', 'd', 'd', ' ', 't', 'e', 's', 't', 's'])
if (characterRoadmap.some(item => item.length === 1)) {
  throw new Error(`Character roadmap was not reassembled: ${JSON.stringify(characterRoadmap)}`)
}

for (const projectType of ['University Project', 'Startup Pitch', 'Research Project', 'Open Source Project']) {
  const report = enrichReport({
    project_id: projectType,
    project_name: projectType,
    project_type: projectType,
    status: 'done',
    overall_score: 70,
    verdict: 'IMPROVE',
    report_id: 'r1',
    evaluations: {
      chief_evaluation: {
        score: 70,
        findings: 'Final Verdict',
      },
    },
    verdict_data: {
      project_type: projectType,
      overall_score: 70,
      verdict: 'IMPROVE',
      risk_level: 'MEDIUM',
      roadmap: [
        'Add automated tests',
        'Improve documentation',
        'Add CI/CD pipeline',
        'Strengthen security controls',
      ],
    },
  })
  const projectPhases = phaseDeploymentRoadmap(report.verdict_data?.roadmap)
  if (projectPhases.length !== 3) {
    throw new Error(`${projectType} roadmap did not render as 3 phases: ${JSON.stringify(projectPhases)}`)
  }
  if (projectPhases.flatMap(phase => phase.items).some(item => item.length === 1)) {
    throw new Error(`${projectType} roadmap rendered character items`)
  }
}

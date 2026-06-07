import { normalizeDisplayList } from '../src/utils/listNormalizer.ts'

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

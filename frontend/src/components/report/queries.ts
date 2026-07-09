import { useQuery } from '@tanstack/react-query'
import { getReport, api } from '../../api/api'

export function useEvaluationReport(projectId: string) {
  return useQuery({
    queryKey: ['report', projectId],
    queryFn: () => getReport(projectId),
    enabled: !!projectId,
    staleTime: 10 * 60 * 1000,
  })
}

export function useRepositoryTree(projectId: string, path?: string) {
  const evalId = projectId
  return useQuery({
    queryKey: ['repo-tree', projectId, path],
    queryFn: async ({ signal }) => {
      const url = path 
        ? `/evaluations/${evalId}/repository-tree?path=${encodeURIComponent(path)}`
        : `/evaluations/${evalId}/repository-tree`
      const res = await api.get(url, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useArchitectureGraph(projectId: string) {
  return useQuery({
    queryKey: ['architecture-graph', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/architecture`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTechnologyGraph(projectId: string) {
  return useQuery({
    queryKey: ['technology-graph', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/technology-graph`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useDependencyGraph(projectId: string) {
  return useQuery({
    queryKey: ['dependency-graph', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/dependency-graph`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCallGraph(projectId: string) {
  return useQuery({
    queryKey: ['call-graph', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/call-graph`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMetrics(projectId: string) {
  return useQuery({
    queryKey: ['metrics', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/metrics`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useHealth(projectId: string) {
  return useQuery({
    queryKey: ['health', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/health`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useHeatmap(projectId: string, metric: string) {
  return useQuery({
    queryKey: ['heatmap', projectId, metric],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/heatmap?metric=${metric}`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useEvidence(projectId: string, page: number = 1, size: number = 50) {
  return useQuery({
    queryKey: ['evidence', projectId, page, size],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/evidence?page=${page}&size=${size}`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRecommendations(projectId: string) {
  return useQuery({
    queryKey: ['recommendations', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/recommendations`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTimeline(projectId: string) {
  return useQuery({
    queryKey: ['timeline', projectId],
    queryFn: async ({ signal }) => {
      // Try evaluation-scoped endpoint first (projectId from URL is evaluation ID).
      // Falls back to project-scoped if the first fails.
      try {
        const res = await api.get(`/evaluations/${projectId}/history`, { signal })
        return res.data
      } catch {
        const res = await api.get(`/projects/${projectId}/history`, { signal })
        return res.data
      }
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useKnowledgeGraph(projectId: string, search: string, tech: string, lang: string, layer: string, collapse: boolean) {
  return useQuery({
    queryKey: ['knowledge-graph', projectId, search, tech, lang, layer, collapse],
    queryFn: async ({ signal }) => {
      let url = `/evaluations/${projectId}/knowledge-graph?collapse=${collapse}`
      if (search) url += `&search=${encodeURIComponent(search)}`
      if (tech) url += `&tech=${encodeURIComponent(tech)}`
      if (lang) url += `&lang=${encodeURIComponent(lang)}`
      if (layer) url += `&layer=${encodeURIComponent(layer)}`
      const res = await api.get(url, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useIntelStatus(projectId: string) {
  return useQuery({
    queryKey: ['intel-status', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/repository-intelligence/status`, { signal })
      return res.data
    },
    enabled: !!projectId,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
    staleTime: 10 * 1000,
    refetchInterval: (query) => {
      const data = query.state.data as any
      if (data && ['completed', 'failed', 'COMPLETED', 'FAILED'].includes(data.status)) {
        return false
      }
      return 3000 // Poll every 3 seconds while running
    },
  })
}

export function useExecutionIntelligence(projectId: string) {
  return useQuery({
    queryKey: ['execution-intelligence', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/execution-intelligence`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAIIntelligence(projectId: string) {
  return useQuery({
    queryKey: ['ai-intelligence', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/ai-intelligence`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCapabilities(projectId: string) {
  return useQuery({
    queryKey: ['capabilities', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/capabilities`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRepositoryStory(projectId: string) {
  return useQuery({
    queryKey: ['repository-story', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/repository-story`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useExecutiveSummary(projectId: string) {
  return useQuery({
    queryKey: ['executive-summary', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/executive-summary`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTraceNodes(projectId: string, node: string) {
  return useQuery({
    queryKey: ['trace-nodes', projectId, node],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/trace-nodes?node=${encodeURIComponent(node)}`, { signal })
      return res.data
    },
    enabled: !!projectId && !!node,
    staleTime: 5 * 60 * 1000,
  })
}

export function useDependencyIntelligence(projectId: string) {
  return useQuery({
    queryKey: ['dependency-intelligence', projectId],
    queryFn: async ({ signal }) => {
      const res = await api.get(`/evaluations/${projectId}/dependency-intelligence`, { signal })
      return res.data
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

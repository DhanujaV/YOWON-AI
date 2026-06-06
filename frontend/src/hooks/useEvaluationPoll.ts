import { useEffect, useState } from 'react'
import { getStatus } from '../api/api'
import type { ProjectStatus } from '../types'

export function useEvaluationPoll(
  projectId: string | undefined,
  onComplete?: (id: string) => void,
) {
  const [status, setStatus] = useState<ProjectStatus>('running')
  const [projectName, setProjectName] = useState('')

  useEffect(() => {
    if (!projectId) return

    let cancelled = false

    const poll = async () => {
      try {
        const data = await getStatus(projectId)
        if (cancelled) return
        setStatus(data.status as ProjectStatus)
        setProjectName(data.name)
        if (data.status === 'done') onComplete?.(projectId)
      } catch {
        /* retry on next interval */
      }
    }

    poll()
    const interval = setInterval(poll, 4000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [projectId, onComplete])

  return { status, projectName }
}

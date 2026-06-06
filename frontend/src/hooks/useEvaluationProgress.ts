import { useEffect, useState, useCallback } from 'react'

import { getStatus, subscribeProgress } from '../api/api'

import type { EvaluationProgress, ProjectStatus, ReportStatus } from '../types'



const DEFAULT_PROGRESS: EvaluationProgress = {

  step: 0,

  total: 8,

  agent: 'coordinator',

  current_task: 'Initializing evaluation pipeline',

  status: 'running',

  evaluation_status: 'running',

  report_status: 'pending',

  elapsed_seconds: 0,

  completion_percent: 0,

  logs: [],

  agent_states: {},

  events: [],

}



function mergeProgress(

  prev: EvaluationProgress,

  incoming: Partial<EvaluationProgress>,

): EvaluationProgress {

  return {

    ...prev,

    ...incoming,

    logs: incoming.logs?.length ? incoming.logs : prev.logs,

    agent_states: incoming.agent_states ?? prev.agent_states,

    events: incoming.events?.length ? incoming.events : prev.events,

  }

}



export function useEvaluationProgress(

  projectId: string | undefined,

  onComplete?: (id: string, meta: { reportStatus: ReportStatus; reportError?: string | null }) => void,

) {

  const [status, setStatus] = useState<ProjectStatus>('running')

  const [reportStatus, setReportStatus] = useState<ReportStatus>('pending')

  const [reportError, setReportError] = useState<string | null>(null)

  const [projectName, setProjectName] = useState('')
  const [projectType, setProjectType] = useState('')

  const [progress, setProgress] = useState<EvaluationProgress>(DEFAULT_PROGRESS)



  const applyStatus = useCallback(

    (

      next: ProjectStatus,

      meta?: { reportStatus?: ReportStatus; reportError?: string | null },

    ) => {

      setStatus(next)

      if (meta?.reportStatus) setReportStatus(meta.reportStatus)

      if (meta?.reportError !== undefined) setReportError(meta.reportError)



      if (next === 'done') {

        onComplete?.(projectId!, {

          reportStatus: meta?.reportStatus ?? reportStatus,

          reportError: meta?.reportError ?? reportError,

        })

      }

      if (next === 'failed') {

        setProgress(p => ({ ...p, status: 'failed', evaluation_status: 'failed' }))

      }

    },

    [onComplete, projectId, reportStatus, reportError],

  )



  useEffect(() => {

    if (!projectId) return



    let cancelled = false

    let es: EventSource | null = null



    const pollStatus = async () => {

      try {

        const data = await getStatus(projectId)

        if (cancelled) return

        setProjectName(data.name)
        setProjectType(data.project_type ?? '')

        const rs = (data.report_status ?? data.progress?.report_status ?? 'pending') as ReportStatus

        const re = data.report_error ?? data.progress?.report_error ?? null

        setReportStatus(rs)

        setReportError(re)

        applyStatus(data.status as ProjectStatus, { reportStatus: rs, reportError: re })

        if (data.progress) {

          setProgress(prev => mergeProgress(prev, {

            step: data.progress!.step ?? 0,

            total: data.progress!.total ?? 8,

            agent: data.progress!.agent ?? 'coordinator',

            current_task: data.progress!.current_task,

            status: (data.progress!.status as EvaluationProgress['status']) ?? 'running',

            evaluation_status: data.evaluation_status ?? data.progress!.evaluation_status,

            report_status: rs,

            report_error: re,

            elapsed_seconds: data.progress!.elapsed_seconds,

            completion_percent: data.progress!.completion_percent,

            logs: data.progress!.logs,

            agent_states: data.progress!.agent_states,

            events: data.progress!.events,

          }))

        }

      } catch {

        /* retry on next poll */

      }

    }



    pollStatus()

    const pollInterval = setInterval(pollStatus, 5000)



    es = subscribeProgress(projectId, (payload) => {

      if (cancelled) return

      const rs = (payload.report_status ?? reportStatus) as ReportStatus

      const re = payload.report_error ?? reportError

      setProgress(prev => mergeProgress(prev, {

        step: payload.step ?? prev.step,

        total: payload.total ?? 8,

        agent: payload.agent ?? prev.agent,

        current_task: payload.current_task ?? prev.current_task,

        status: payload.status ?? prev.status,

        evaluation_status: payload.evaluation_status ?? prev.evaluation_status,

        report_status: payload.report_status ?? prev.report_status,

        report_error: payload.report_error ?? prev.report_error,

        elapsed_seconds: payload.elapsed_seconds ?? prev.elapsed_seconds,

        completion_percent: payload.completion_percent ?? prev.completion_percent,

        logs: payload.logs ?? prev.logs,

        agent_states: payload.agent_states ?? prev.agent_states,

        events: payload.events ?? prev.events,

      }))

      if (payload.report_status) setReportStatus(payload.report_status)

      if (payload.report_error !== undefined) setReportError(payload.report_error)

      if (payload.status === 'done') {

        applyStatus('done', { reportStatus: rs, reportError: re })

      }

      if (payload.status === 'failed') applyStatus('failed')

    })



    return () => {

      cancelled = true

      clearInterval(pollInterval)

      es?.close()

    }

  }, [projectId, applyStatus])



  return { status, reportStatus, reportError, projectName, projectType, progress }

}


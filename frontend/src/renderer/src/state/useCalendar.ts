/**
 * One calendar over a month: the individual one (merged across my projects) or a project's.
 *
 * The range requested is the whole visible grid, so a deadline or event on the borrowed days at
 * either edge is drawn where it belongs.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'

import type { ApiError, CalendarRange } from '@shared/types'

import { monthRange } from '../lib/calendar'

export interface CalendarScope {
  kind: 'personal' | 'project'
  projectId?: string
}

export function useCalendar(scope: CalendarScope, year: number, month: number) {
  const [range, setRange] = useState<CalendarRange | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<ApiError | null>(null)

  const grid = useMemo(() => monthRange(year, month), [year, month])
  const { from, to } = grid
  const projectId = scope.projectId

  const reload = useCallback(async (): Promise<void> => {
    setStatus('loading')
    setError(null)
    const result =
      scope.kind === 'project' && projectId
        ? await window.jyteams.calendar.project({ projectId, from, to })
        : await window.jyteams.calendar.personal({ from, to })
    if (result.ok) {
      setRange(result.data)
      setStatus('ready')
    } else {
      setRange(null)
      setError(result.error)
      setStatus('error')
    }
  }, [scope.kind, projectId, from, to])

  useEffect(() => {
    void reload()
  }, [reload])

  return { range, grid, status, error, reload }
}

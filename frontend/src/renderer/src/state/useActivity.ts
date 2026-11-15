import { useCallback, useEffect, useState } from 'react'

import type { ApiError, TicketEvent } from '@shared/types'

/** The changes-and-updates feed. `revision` forces a re-read after a write. */
export function useActivity(
  input: { projectId?: string; ticketId?: string },
  enabled: boolean,
  revision: number
) {
  const [events, setEvents] = useState<TicketEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const { projectId, ticketId } = input

  const reload = useCallback(async (): Promise<void> => {
    if (!enabled) return
    setLoading(true)
    setError(null)
    const result = await window.jyteams.tickets.activity({
      projectId: projectId || undefined,
      ticketId: ticketId || undefined,
      limit: 100
    })
    if (result.ok) {
      setEvents(result.data)
    } else {
      setEvents([])
      setError(result.error)
    }
    setLoading(false)
  }, [enabled, projectId, ticketId])

  useEffect(() => {
    void reload()
  }, [reload, revision])

  return { events, loading, error, reload }
}

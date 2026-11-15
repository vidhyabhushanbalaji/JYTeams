import { useCallback, useEffect, useState } from 'react'

import type { ApiError, Ticket, TicketStatus } from '@shared/types'

export interface TicketFilters {
  scope: 'mine' | 'project'
  projectId?: string
  status?: TicketStatus | null
}

/** The ticket list for the current filters. Reloads whenever a filter changes. */
export function useTickets(filters: TicketFilters, enabled: boolean) {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const { scope, projectId, status } = filters

  const reload = useCallback(async (): Promise<void> => {
    if (!enabled) return
    setLoading(true)
    setError(null)
    const result = await window.jyteams.tickets.list({
      scope,
      projectId: projectId || undefined,
      status: status ?? null
    })
    if (result.ok) {
      setTickets(result.data)
    } else {
      setTickets([])
      setError(result.error)
    }
    setLoading(false)
  }, [enabled, scope, projectId, status])

  useEffect(() => {
    void reload()
  }, [reload])

  return { tickets, loading, error, reload }
}

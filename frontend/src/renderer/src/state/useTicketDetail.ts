import { useCallback, useEffect, useState } from 'react'

import type { ApiError, TicketDetail } from '@shared/types'

/** One ticket, with its comments and its (cached) files. */
export function useTicketDetail(ticketId: string | null) {
  const [detail, setDetail] = useState<TicketDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const reload = useCallback(
    async (refresh = false): Promise<void> => {
      if (!ticketId) {
        setDetail(null)
        return
      }
      setLoading(true)
      setError(null)
      const result = await window.jyteams.tickets.get(ticketId, refresh)
      if (result.ok) {
        setDetail(result.data)
      } else {
        setDetail(null)
        setError(result.error)
      }
      setLoading(false)
    },
    [ticketId]
  )

  useEffect(() => {
    void reload()
  }, [reload])

  return { detail, loading, error, reload, setDetail }
}

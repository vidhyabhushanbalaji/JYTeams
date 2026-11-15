/**
 * The calendar events whose notes mention one ticket.
 *
 * Read from the calendar section's `mentioning` route, so the ticket panel never parses notes and
 * never copies an event onto the ticket; a mention added in either place shows up on the next
 * open (or refresh).
 */

import { useCallback, useEffect, useState } from 'react'

import type { ApiError, CalendarItem } from '@shared/types'

export function useTicketCalendar(projectId: string | null, ticketId: string | null) {
  const [events, setEvents] = useState<CalendarItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const reload = useCallback(async (): Promise<void> => {
    if (!projectId || !ticketId) {
      setEvents([])
      setLoading(false)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    const result = await window.jyteams.calendar.mentioning({
      projectId,
      kind: 'ticket',
      id: ticketId
    })
    if (result.ok) {
      setEvents(result.data)
    } else {
      setEvents([])
      setError(result.error)
    }
    setLoading(false)
  }, [projectId, ticketId])

  useEffect(() => {
    void reload()
  }, [reload])

  return { events, loading, error, reload }
}

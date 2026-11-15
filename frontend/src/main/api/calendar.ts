/**
 * The calendar API: one calendar per project, and the individual one that merges them.
 *
 * Ticket deadlines are computed by the backend from the tickets themselves, so nothing here has
 * to reload a ticket after it changes — a fresh read of the range is always current.
 */

import type {
  CalendarEvent,
  CalendarEventInput,
  CalendarEventPatch,
  CalendarRange
} from '../../shared/types'
import { request, requestVoid } from './client'

const BASE = '/api/calendar'
const JSON_HEADERS = { 'Content-Type': 'application/json' }
const id = encodeURIComponent

export const personalCalendar = (input: { from: string; to: string }): Promise<CalendarRange> => {
  const params = new URLSearchParams({ from: input.from, to: input.to })
  return request(`${BASE}/personal?${params.toString()}`)
}

export const projectCalendar = (input: {
  projectId: string
  from: string
  to: string
}): Promise<CalendarRange> => {
  const params = new URLSearchParams({ from: input.from, to: input.to })
  return request(`${BASE}/projects/${id(input.projectId)}?${params.toString()}`)
}

export const createEvent = (input: CalendarEventInput): Promise<CalendarEvent> =>
  request(`${BASE}/events`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({
      project_id: input.projectId ?? null,
      title: input.title,
      notes: input.notes ?? '',
      starts_at: input.startsAt,
      ends_at: input.endsAt ?? null,
      all_day: input.allDay ?? false
    })
  })

export function updateEvent(eventId: string, patch: CalendarEventPatch): Promise<CalendarEvent> {
  // Only the fields that were sent are applied, so `null` can mean "clear the end time".
  const body: Record<string, unknown> = {}
  if ('title' in patch) body.title = patch.title
  if ('notes' in patch) body.notes = patch.notes
  if ('startsAt' in patch) body.starts_at = patch.startsAt
  if ('endsAt' in patch) body.ends_at = patch.endsAt
  if ('allDay' in patch) body.all_day = patch.allDay
  return request(`${BASE}/events/${id(eventId)}`, {
    method: 'PATCH',
    headers: JSON_HEADERS,
    body: JSON.stringify(body)
  })
}

export const deleteEvent = (eventId: string): Promise<null> =>
  requestVoid(`${BASE}/events/${id(eventId)}`, { method: 'DELETE' })

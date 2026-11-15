/**
 * The tickets API: identity, sharing, tickets, their files, comments and the activity feed.
 *
 * The renderer never talks to a model. The backend distils a ticket's wording into a short search
 * query once (cached with the Graph AI Search result on the ticket row), so opening a ticket is a
 * read and `refresh` re-runs only the model-free search.
 */

import type {
  Member,
  ProjectMember,
  Ticket,
  TicketComment,
  TicketDetail,
  TicketEvent,
  TicketFiles,
  TicketInput,
  TicketPatch,
  TicketStatus
} from '../../shared/types'
import { request, requestVoid } from './client'

const BASE = '/api/tickets'
const JSON_HEADERS = { 'Content-Type': 'application/json' }
const id = encodeURIComponent

export const listMembers = (): Promise<Member[]> => request(`${BASE}/members`)

export const signIn = (displayName: string): Promise<Member> =>
  request(`${BASE}/members`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ display_name: displayName })
  })

export const currentMember = (): Promise<Member> => request(`${BASE}/me`)

export function listTickets(input: {
  scope?: 'mine' | 'project'
  projectId?: string
  status?: TicketStatus | null
  limit?: number
}): Promise<Ticket[]> {
  const params = new URLSearchParams({ scope: input.scope ?? 'mine' })
  if (input.projectId) params.set('project_id', input.projectId)
  if (input.status) params.set('status', input.status)
  params.set('limit', String(input.limit ?? 200))
  return request(`${BASE}/tickets?${params.toString()}`)
}

export const createTicket = (input: TicketInput): Promise<Ticket> =>
  request(`${BASE}/tickets`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({
      project_id: input.projectId,
      title: input.title,
      description: input.description ?? '',
      assignee_id: input.assigneeId ?? null,
      priority: input.priority ?? 'medium',
      due_date: input.dueDate ?? null,
      labels: input.labels ?? []
    })
  })

export const getTicket = (ticketId: string, refresh = false): Promise<TicketDetail> =>
  request(`${BASE}/tickets/${id(ticketId)}${refresh ? '?refresh=true' : ''}`)

export function updateTicket(ticketId: string, patch: TicketPatch): Promise<Ticket> {
  // Only the fields that were sent are applied, so `null` can mean "clear".
  const body: Record<string, unknown> = {}
  if ('title' in patch) body.title = patch.title
  if ('description' in patch) body.description = patch.description
  if ('assigneeId' in patch) body.assignee_id = patch.assigneeId
  if ('priority' in patch) body.priority = patch.priority
  if ('dueDate' in patch) body.due_date = patch.dueDate
  if ('labels' in patch) body.labels = patch.labels
  return request(`${BASE}/tickets/${id(ticketId)}`, {
    method: 'PATCH',
    headers: JSON_HEADERS,
    body: JSON.stringify(body)
  })
}

export const setStatus = (ticketId: string, status: TicketStatus): Promise<Ticket> =>
  request(`${BASE}/tickets/${id(ticketId)}/status`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ status })
  })

export const ticketFiles = (ticketId: string, refresh = false): Promise<TicketFiles> =>
  request(`${BASE}/tickets/${id(ticketId)}/files${refresh ? '?refresh=true' : ''}`)

export const attachFile = (
  ticketId: string,
  fileId: string,
  source: 'upload' | 'existing' = 'existing'
): Promise<TicketFiles> =>
  request(`${BASE}/tickets/${id(ticketId)}/files`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ file_id: fileId, source })
  })

export const detachFile = (ticketId: string, fileId: string): Promise<null> =>
  requestVoid(`${BASE}/tickets/${id(ticketId)}/files/${id(fileId)}`, { method: 'DELETE' })

export const addComment = (ticketId: string, body: string): Promise<TicketComment> =>
  request(`${BASE}/tickets/${id(ticketId)}/comments`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ body })
  })

export function listActivity(input: {
  projectId?: string
  ticketId?: string
  limit?: number
}): Promise<TicketEvent[]> {
  const params = new URLSearchParams({ limit: String(input.limit ?? 100) })
  if (input.projectId) params.set('project_id', input.projectId)
  if (input.ticketId) params.set('ticket_id', input.ticketId)
  return request(`${BASE}/activity?${params.toString()}`)
}

export const listProjectMembers = (projectId: string): Promise<ProjectMember[]> =>
  request(`${BASE}/projects/${id(projectId)}/members`)

export const shareProject = (projectId: string, memberId: string): Promise<Member> =>
  request(`${BASE}/projects/${id(projectId)}/members`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ member_id: memberId })
  })

export const unshareProject = (projectId: string, memberId: string): Promise<null> =>
  requestVoid(`${BASE}/projects/${id(projectId)}/members/${id(memberId)}`, { method: 'DELETE' })

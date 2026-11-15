/** Pure helpers for the tickets page: labels, grouping, initials, the feed's sentences. */

import type { Ticket, TicketEvent, TicketPriority, TicketStatus } from '@shared/types'

export const STATUS_LABEL: Record<TicketStatus, string> = {
  todo: 'To do',
  in_progress: 'In progress',
  done: 'Done'
}

export const PRIORITY_LABEL: Record<TicketPriority, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High'
}

/** Smaller is more urgent, so a sort can be a plain comparison. */
export const PRIORITY_RANK: Record<TicketPriority, number> = { high: 0, medium: 1, low: 2 }

export const ticketKey = (ticket: Pick<Ticket, 'number'>): string => `#${ticket.number}`

export function initials(displayName: string): string {
  const parts = displayName.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

export interface DueLabel {
  text: string
  overdue: boolean
}

/** A due date as "Today", "Tomorrow", or a short date, plus whether it is overdue. */
export function dueLabel(iso: string | null, now: Date = new Date()): DueLabel {
  if (!iso) return { text: '', overdue: false }
  const due = new Date(`${iso.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(due.getTime())) return { text: '', overdue: false }

  const startOfDay = (value: Date): number =>
    new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime()
  const days = Math.round((startOfDay(due) - startOfDay(now)) / 86_400_000)

  if (days === 0) return { text: 'Today', overdue: false }
  if (days === 1) return { text: 'Tomorrow', overdue: false }
  const text = due.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
  return { text: days < 0 ? `${text} (overdue)` : text, overdue: days < 0 }
}

/** "just now", "12m ago", "3h ago", "5d ago" — measured against a supplied clock. */
export function relativeTime(iso: string | null, now: Date = new Date()): string {
  if (!iso) return ''
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  const seconds = Math.max(0, Math.round((now.getTime() - moment.getTime()) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}d ago`
  return moment.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export interface ProjectGroup {
  projectId: string
  projectName: string
  tickets: Ticket[]
}

/** Group tickets by project, keeping the order the projects first appear in. */
export function groupByProject(tickets: Ticket[]): ProjectGroup[] {
  const groups = new Map<string, ProjectGroup>()
  for (const ticket of tickets) {
    const existing = groups.get(ticket.project_id)
    if (existing) {
      existing.tickets.push(ticket)
    } else {
      groups.set(ticket.project_id, {
        projectId: ticket.project_id,
        projectName: ticket.project_name || 'Project',
        tickets: [ticket]
      })
    }
  }
  return [...groups.values()]
}

/** The next/previous index in a list, wrapping at both ends. */
export function stepIndex(current: number, length: number, direction: 1 | -1): number {
  if (length <= 0) return 0
  return (current + direction + length) % length
}

export interface MatchTarget {
  fileId: string
  directoryPath: string
  name: string
}

/** The files a ticket points at, in the order the graph should step through them. */
export function matchTargets(
  attached: { file_id: string; directory_path: string; name: string }[],
  suggested: { file_id: string; directory_path: string; name: string }[]
): MatchTarget[] {
  const seen = new Set<string>()
  const targets: MatchTarget[] = []
  for (const file of [...attached, ...suggested]) {
    if (seen.has(file.file_id)) continue
    seen.add(file.file_id)
    targets.push({ fileId: file.file_id, directoryPath: file.directory_path, name: file.name })
  }
  return targets
}

const detailString = (event: TicketEvent, key: string): string => {
  const value = event.detail[key]
  return typeof value === 'string' ? value : ''
}

const detailNumber = (event: TicketEvent, key: string): number | null => {
  const value = event.detail[key]
  return typeof value === 'number' ? value : null
}

/** The feed sentence for one event. Unknown kinds fall back to the raw kind. */
export function eventText(event: TicketEvent): string {
  const number = detailNumber(event, 'number') ?? event.ticket_number
  const label = number ? `#${number}` : 'a ticket'
  const who = event.actor?.display_name ?? 'Someone'

  switch (event.kind) {
    case 'ticket_created': {
      const title = detailString(event, 'title')
      const assignee = detailString(event, 'assignee_name')
      const target = assignee && assignee !== who ? ` and assigned it to ${assignee}` : ''
      return `${who} created ${label}${title ? ` — ${title}` : ''}${target}.`
    }
    case 'ticket_assigned': {
      const assignee = detailString(event, 'assignee_name')
      return assignee
        ? `${who} assigned ${label} to ${assignee}.`
        : `${who} unassigned ${label}.`
    }
    case 'ticket_completed':
      return `${who} completed ${label}.`
    case 'ticket_reopened':
      return `${who} reopened ${label}.`
    case 'ticket_status_changed': {
      const from = detailString(event, 'from').replace('_', ' ')
      const to = detailString(event, 'to').replace('_', ' ')
      return `${who} moved ${label} from ${from || 'todo'} to ${to || 'in progress'}.`
    }
    case 'ticket_updated': {
      const fields = Array.isArray(event.detail.fields) ? (event.detail.fields as string[]) : []
      const what = fields.length > 0 ? fields.join(', ') : 'the details'
      return `${who} edited ${what} on ${label}.`
    }
    case 'ticket_commented':
      return `${who} commented on ${label}.`
    case 'file_attached': {
      const file = detailString(event, 'file_name') || 'a document'
      const source = detailString(event, 'source')
      return source === 'upload'
        ? `${who} uploaded ${file} and put it on ${label}.`
        : `${who} attached ${file} to ${label}.`
    }
    case 'file_detached': {
      const file = detailString(event, 'file_name') || 'a document'
      return `${who} took ${file} off ${label}.`
    }
    case 'file_added': {
      const file = detailString(event, 'file_name') || 'a document'
      const folder = detailString(event, 'directory_path') || 'the project root'
      return `${who} added ${file} to ${folder}.`
    }
    case 'files_uploaded': {
      const files = detailNumber(event, 'files') ?? 0
      const project = detailString(event, 'project_name') || 'a project'
      const suffix = files === 1 ? 'file' : 'files'
      return `${who} uploaded ${files} ${suffix} to ${project}.`
    }
    case 'document_saved': {
      const file = detailString(event, 'file_name') || 'a document'
      return `${who} saved ${file}.`
    }
    case 'project_shared': {
      const member = detailString(event, 'member_name') || 'a teammate'
      const project = detailString(event, 'project_name') || 'a project'
      return `${who} shared ${project} with ${member}.`
    }
    case 'project_member_removed': {
      const member = detailString(event, 'member_name') || 'a teammate'
      const project = detailString(event, 'project_name') || 'a project'
      return `${who} stopped sharing ${project} with ${member}.`
    }
    default:
      return `${who} · ${event.kind.replaceAll('_', ' ')}`
  }
}

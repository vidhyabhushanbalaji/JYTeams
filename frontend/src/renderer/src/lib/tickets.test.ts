import { describe, expect, it } from 'vitest'

import type { Ticket, TicketEvent } from '@shared/types'

import {
  dueLabel,
  eventText,
  groupByProject,
  initials,
  matchTargets,
  relativeTime,
  stepIndex,
  ticketKey
} from './tickets'

function ticket(overrides: Partial<Ticket>): Ticket {
  return {
    id: 'ticket-1',
    project_id: 'project-1',
    project_name: 'Pulse',
    number: 1,
    title: 'Fix login',
    description: '',
    status: 'todo',
    priority: 'medium',
    due_date: null,
    labels: [],
    assignee: null,
    reporter: null,
    completed_at: null,
    completed_by: null,
    attachment_count: 0,
    comment_count: 0,
    created_at: null,
    updated_at: null,
    ...overrides
  }
}

function event(overrides: Partial<TicketEvent>): TicketEvent {
  return {
    id: 'event-1',
    kind: 'ticket_created',
    detail: {},
    project_id: 'project-1',
    ticket_id: 'ticket-1',
    ticket_number: 7,
    actor: { id: 'member-1', display_name: 'Ada Lovelace' },
    created_at: null,
    ...overrides
  }
}

describe('initials', () => {
  it('takes the first and last initial', () => {
    expect(initials('Ada Lovelace')).toBe('AL')
  })

  it('handles one name and blanks', () => {
    expect(initials('Ada')).toBe('AD')
    expect(initials('   ')).toBe('?')
  })
})

describe('ticketKey', () => {
  it('renders the project-local number', () => {
    expect(ticketKey({ number: 12 })).toBe('#12')
  })
})

describe('dueLabel', () => {
  const now = new Date('2026-03-10T09:00:00')

  it('says Today and Tomorrow', () => {
    expect(dueLabel('2026-03-10', now)).toEqual({ text: 'Today', overdue: false })
    expect(dueLabel('2026-03-11', now)).toEqual({ text: 'Tomorrow', overdue: false })
  })

  it('flags an overdue date', () => {
    const label = dueLabel('2026-03-01', now)
    expect(label.overdue).toBe(true)
    expect(label.text).toContain('overdue')
  })

  it('is silent without a date', () => {
    expect(dueLabel(null, now)).toEqual({ text: '', overdue: false })
  })
})

describe('relativeTime', () => {
  const now = new Date('2026-03-10T12:00:00Z')

  it('reads like a feed', () => {
    expect(relativeTime('2026-03-10T11:59:40Z', now)).toBe('just now')
    expect(relativeTime('2026-03-10T11:48:00Z', now)).toBe('12m ago')
    expect(relativeTime('2026-03-10T08:00:00Z', now)).toBe('4h ago')
    expect(relativeTime('2026-03-07T12:00:00Z', now)).toBe('3d ago')
  })

  it('handles a missing timestamp', () => {
    expect(relativeTime(null, now)).toBe('')
  })
})

describe('groupByProject', () => {
  it('keeps project order and groups their tickets', () => {
    const groups = groupByProject([
      ticket({ id: 'a', project_id: 'p1', project_name: 'Pulse' }),
      ticket({ id: 'b', project_id: 'p2', project_name: 'Atlas' }),
      ticket({ id: 'c', project_id: 'p1', project_name: 'Pulse' })
    ])

    expect(groups.map((group) => group.projectId)).toEqual(['p1', 'p2'])
    expect(groups[0].tickets.map((item) => item.id)).toEqual(['a', 'c'])
  })
})

describe('stepIndex', () => {
  it('wraps in both directions', () => {
    expect(stepIndex(0, 3, -1)).toBe(2)
    expect(stepIndex(2, 3, 1)).toBe(0)
    expect(stepIndex(0, 0, 1)).toBe(0)
  })
})

describe('matchTargets', () => {
  it('puts attached files first and removes duplicates', () => {
    const targets = matchTargets(
      [{ file_id: 'a', directory_path: 'pulse/auth', name: 'a.md' }],
      [
        { file_id: 'a', directory_path: 'pulse/auth', name: 'a.md' },
        { file_id: 'b', directory_path: 'pulse', name: 'b.md' }
      ]
    )

    expect(targets.map((target) => target.fileId)).toEqual(['a', 'b'])
  })
})

describe('eventText', () => {
  it('describes a completion', () => {
    expect(eventText(event({ kind: 'ticket_completed' }))).toBe('Ada Lovelace completed #7.')
  })

  it('describes an upload', () => {
    const text = eventText(
      event({
        kind: 'file_attached',
        detail: { file_name: 'auth.md', source: 'upload' }
      })
    )
    expect(text).toBe('Ada Lovelace uploaded auth.md and put it on #7.')
  })

  it('describes a project upload with a count', () => {
    const text = eventText(
      event({
        kind: 'files_uploaded',
        ticket_number: null,
        detail: { files: 3, project_name: 'Pulse' }
      })
    )
    expect(text).toBe('Ada Lovelace uploaded 3 files to Pulse.')
  })

  it('falls back to the raw kind for an unknown event', () => {
    expect(eventText(event({ kind: 'something_new' }))).toContain('something new')
  })
})

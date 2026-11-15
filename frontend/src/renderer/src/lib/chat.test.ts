import { describe, expect, it } from 'vitest'

import type { ChatMessage } from '@shared/types'

import {
  dayLabel,
  groupByDay,
  lastSeq,
  mentionDraft,
  mentionIcon,
  mentionMarker,
  mentionQueryAt,
  mentionText,
  mergeMessages,
  messagePreview,
  plainBody,
  segmentsOf
} from './chat'

const mention = {
  kind: 'file' as const,
  id: 'f-1',
  label: 'auth.md',
  path: 'guides/auth.md',
  directory_path: 'guides',
  ticket_number: null,
  event_day: null
}

function message(overrides: Partial<ChatMessage>): ChatMessage {
  return {
    seq: 1,
    id: 'm-1',
    project_id: 'p-1',
    author: { id: 'ada', display_name: 'Ada Lovelace' },
    body: 'hello',
    mentions: [],
    created_at: '2026-03-02T10:00:00+00:00',
    deleted: false,
    ...overrides
  }
}

describe('chat markers', () => {
  it('builds the marker the composer inserts', () => {
    expect(mentionMarker({ kind: 'directory', id: 'd-1', label: 'guides' })).toBe(
      '@[guides](directory:d-1)'
    )
  })

  it('splits a body into text and resolved mentions', () => {
    const body = 'read @[auth.md](file:f-1) before you deploy'
    const segments = segmentsOf({ body, mentions: [mention] })

    expect(segments.map((segment) => segment.kind)).toEqual(['text', 'mention', 'text'])
    expect(segments[1]).toMatchObject({ mention: { id: 'f-1' } })
  })

  it('leaves a marker that did not resolve as plain text', () => {
    const segments = segmentsOf({ body: 'see @[gone](file:f-9)', mentions: [] })

    expect(segments).toEqual([{ kind: 'text', text: 'see @[gone](file:f-9)' }])
  })

  it('reads a ticket mention with its number', () => {
    expect(
      mentionText({ ...mention, kind: 'ticket', id: 't-1', label: 'Fix it', ticket_number: 12 })
    ).toBe('#12 Fix it')
    expect(mentionText(mention)).toBe('auth.md')
  })

  it('resolves an event marker like every other kind', () => {
    const event = {
      ...mention,
      kind: 'event' as const,
      id: 'e-1',
      label: 'Kickoff',
      path: '',
      directory_path: '',
      event_day: '2026-03-03'
    }
    const segments = segmentsOf({ body: 'notes from @[Kickoff](event:e-1)', mentions: [event] })

    expect(segments[1]).toMatchObject({ mention: { kind: 'event', event_day: '2026-03-03' } })
    expect(mentionIcon('event')).toBe('\u{1F4C5}')
  })

  it('writes the draft another screen pre-fills', () => {
    expect(
      mentionDraft({ kind: 'event', id: 'e-1', label: 'Kickoff', ticket_number: null })
    ).toBe('@[Kickoff](event:e-1) ')
    expect(
      mentionDraft({ kind: 'ticket', id: 't-1', label: 'Fix it', ticket_number: 12 })
    ).toBe('@[#12 Fix it](ticket:t-1) ')
  })
})

describe('message previews and grouping', () => {
  it('turns markers into @names and bounds the length', () => {
    expect(messagePreview(message({ body: 'read @[auth.md](file:f-1) now' }))).toBe('read @auth.md now')
    expect(plainBody('see @[auth.md](file:f-1)')).toBe('see @auth.md')
    expect(messagePreview(message({ body: 'x'.repeat(200) }), 10)).toHaveLength(10)
    expect(messagePreview(message({ deleted: true }))).toBe('Message removed')
    expect(messagePreview(null)).toBe('No messages yet')
  })

  it('groups messages by their local day, oldest first', () => {
    const groups = groupByDay([
      message({ id: 'a', seq: 1, created_at: '2026-03-02T09:00:00' }),
      message({ id: 'b', seq: 2, created_at: '2026-03-03T09:00:00' }),
      message({ id: 'c', seq: 3, created_at: '2026-03-02T18:00:00' })
    ])

    expect(groups.map((group) => group.day)).toEqual(['2026-03-02', '2026-03-03'])
    expect(groups[0].messages.map((item) => item.id)).toEqual(['a', 'c'])
  })

  it('names today and yesterday', () => {
    const now = new Date(2026, 2, 3, 12, 0, 0)

    expect(dayLabel('2026-03-03', now)).toBe('Today')
    expect(dayLabel('2026-03-02', now)).toBe('Yesterday')
    expect(dayLabel('2026-02-20', now)).toContain('20')
  })

  it('merges a poll page without duplicating or reordering', () => {
    const merged = mergeMessages(
      [message({ id: 'b', seq: 2 }), message({ id: 'a', seq: 1 })],
      [message({ id: 'c', seq: 3 }), message({ id: 'b', seq: 2, body: 'edited' })]
    )

    expect(merged.map((item) => item.id)).toEqual(['a', 'b', 'c'])
    expect(merged[1].body).toBe('edited')
    expect(lastSeq(merged)).toBe(3)
  })
})

describe('mentionQueryAt', () => {
  it('finds the word being typed after an @', () => {
    expect(mentionQueryAt('look at @auth', 13)).toEqual({ start: 8, query: 'auth' })
    expect(mentionQueryAt('@', 1)).toEqual({ start: 0, query: '' })
  })

  it('does not trigger in the middle of a word', () => {
    expect(mentionQueryAt('mail me at ada@example.com', 24)).toBeNull()
    expect(mentionQueryAt('no mention here', 15)).toBeNull()
  })
})

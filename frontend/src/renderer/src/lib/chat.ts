/**
 * Pure helpers for the chat page: turning a body with mention markers into text and chips, day
 * grouping, previews, and the marker the picker inserts.
 *
 * The marker syntax is the backend's (`app/chat/mentions.py`): `@[label](kind:id)`.
 */

import type { ChatMention, ChatMessage, MentionKind, MentionTarget } from '@shared/types'

export type ChatSegment =
  | { kind: 'text'; text: string }
  | { kind: 'mention'; mention: ChatMention; raw: string }

const MARKER = /@\[([^[\]\n]{1,120})\]\((file|directory|ticket|event):([^()\s]{1,64})\)/g

export const mentionMarker = (
  target: Pick<MentionTarget, 'kind' | 'id' | 'label'>
): string => {
  const label = target.label.replace(/[[\]\n]/g, ' ').replace(/\s+/g, ' ').trim() || 'item'
  return `@[${label}](${target.kind}:${target.id})`
}

/** Break a body into plain text and resolved mentions (unknown markers stay as text). */
export function segmentsOf(
  message: Pick<ChatMessage, 'body' | 'mentions'>
): ChatSegment[] {
  const byKey = new Map(message.mentions.map((item) => [`${item.kind}:${item.id}`, item]))
  const segments: ChatSegment[] = []
  let cursor = 0

  for (const match of message.body.matchAll(MARKER)) {
    const index = match.index ?? 0
    if (index > cursor) {
      segments.push({ kind: 'text', text: message.body.slice(cursor, index) })
    }
    const mention = byKey.get(`${match[2]}:${match[3]}`)
    if (mention) {
      segments.push({ kind: 'mention', mention, raw: match[0] })
    } else {
      segments.push({ kind: 'text', text: match[0] })
    }
    cursor = index + match[0].length
  }

  if (cursor < message.body.length) {
    segments.push({ kind: 'text', text: message.body.slice(cursor) })
  }

  // Merge neighbouring text so a marker that did not resolve reads as one plain sentence.
  const merged: ChatSegment[] = []
  for (const segment of segments) {
    const previous = merged[merged.length - 1]
    if (segment.kind === 'text' && previous?.kind === 'text') {
      merged[merged.length - 1] = { kind: 'text', text: previous.text + segment.text }
    } else if (segment.kind === 'text' && segment.text.length === 0) {
      continue
    } else {
      merged.push(segment)
    }
  }
  return merged
}

/** How a mention reads in a message: a ticket keeps its number, everything else its name. */
export function mentionText(mention: ChatMention): string {
  if (mention.kind === 'ticket' && mention.ticket_number !== null) {
    return `#${mention.ticket_number} ${mention.label}`
  }
  return mention.label
}

export const mentionIcon = (kind: MentionKind): string =>
  kind === 'file'
    ? '\u{1F4C4}'
    : kind === 'directory'
      ? '\u{1F4C1}'
      : kind === 'ticket'
        ? '\u{1F3AB}'
        : '\u{1F4C5}'

/** What pressing a chip does, in the chip's tooltip. */
export const mentionOpenHint = (kind: MentionKind): string =>
  kind === 'ticket'
    ? 'Open this ticket'
    : kind === 'event'
      ? 'Open this event on the calendar'
      : 'Open this in the project graph'

/**
 * The marker another screen pre-fills when it starts a message about something.
 *
 * A ticket keeps its number in the text the reader sees (`#12 Fix it`); the backend resolves the
 * rest and the chip adds the number back through :func:`mentionText`.
 */
export function mentionDraft(
  target: Pick<ChatMention, 'kind' | 'id' | 'label' | 'ticket_number'>
): string {
  const label =
    target.kind === 'ticket' && target.ticket_number !== null
      ? `#${target.ticket_number} ${target.label}`
      : target.label
  return `${mentionMarker({ kind: target.kind, id: target.id, label })} `
}

/** A body with every marker turned into `@label` — for text drawn without chips. */
export const plainBody = (body: string): string =>
  body.replace(MARKER, (_match, label: string) => `@${label}`)

/** A one-line preview for the channel list: markers become `@name`. */
export function messagePreview(message: ChatMessage | null, limit = 80): string {
  if (!message) return 'No messages yet'
  if (message.deleted) return 'Message removed'
  const flat = plainBody(message.body).replace(/\s+/g, ' ').trim()
  return flat.length > limit ? `${flat.slice(0, limit - 1)}\u2026` : flat
}

export interface MessageDay {
  /** `YYYY-MM-DD` in local time. */
  day: string
  messages: ChatMessage[]
}

export const localDay = (iso: string | null): string => {
  const moment = iso ? new Date(iso) : new Date()
  if (Number.isNaN(moment.getTime())) return ''
  const month = `${moment.getMonth() + 1}`.padStart(2, '0')
  const day = `${moment.getDate()}`.padStart(2, '0')
  return `${moment.getFullYear()}-${month}-${day}`
}

/** The day of a message, as the chat header words it. */
export function dayLabel(day: string, now: Date = new Date()): string {
  if (!day) return ''
  if (day === localDay(now.toISOString())) return 'Today'
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (day === localDay(yesterday.toISOString())) return 'Yesterday'
  const [year, month, date] = day.split('-').map(Number)
  return new Date(year, month - 1, date).toLocaleDateString(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short'
  })
}

export function groupByDay(messages: ChatMessage[]): MessageDay[] {
  const groups = new Map<string, ChatMessage[]>()
  for (const message of messages) {
    const day = localDay(message.created_at)
    const bucket = groups.get(day)
    if (bucket) bucket.push(message)
    else groups.set(day, [message])
  }
  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([day, rows]) => ({ day, messages: rows }))
}

/** Merge a poll page into the list: no duplicates, chronological by `seq`. */
export function mergeMessages(current: ChatMessage[], incoming: ChatMessage[]): ChatMessage[] {
  const byId = new Map(current.map((message) => [message.id, message]))
  for (const message of incoming) byId.set(message.id, message)
  return [...byId.values()].sort((left, right) => left.seq - right.seq)
}

export const lastSeq = (messages: ChatMessage[]): number =>
  messages.reduce((highest, message) => Math.max(highest, message.seq), 0)

/** The `@word` being typed before the caret, if any — what the picker searches for. */
export function mentionQueryAt(
  text: string,
  caret: number
): { start: number; query: string } | null {
  const before = text.slice(0, caret)
  const match = /(^|\s)@([^\s@]{0,60})$/.exec(before)
  if (!match) return null
  return { start: before.length - match[2].length - 1, query: match[2] }
}

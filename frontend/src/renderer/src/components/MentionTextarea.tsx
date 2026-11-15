/**
 * A textarea that can point at something: typing `@` opens the picker and inserting a target
 * writes the same `@[label](kind:id)` marker chat writes.
 *
 * Two screens share it — the chat composer (documents, folders, tickets and calendar events) and
 * an event's notes (documents, folders and tickets) — so the marker grammar has one UI.
 */

import { useEffect, useRef, useState, type KeyboardEvent } from 'react'

import type { MentionTarget } from '@shared/types'

import { mentionMarker, mentionQueryAt } from '../lib/chat'
import { useMentionTargets } from '../state/useMentionTargets'
import { MentionPicker } from './MentionPicker'

export function MentionTextarea({
  projectId,
  value,
  onChange,
  rows = 2,
  maxLength = 4_000,
  placeholder,
  className = 'field__input field__input--area',
  pickerTitle,
  onSubmit,
  focusKey
}: {
  /** The project whose documents, folders, tickets and events may be mentioned. */
  projectId: string | null
  value: string
  /** The next value and where the caret should sit after a change. */
  onChange: (value: string, caret: number) => void
  rows?: number
  maxLength?: number
  placeholder?: string
  className?: string
  /** The picker's heading; screens word it for what they offer. */
  pickerTitle?: string
  /** Enter without Shift, when the screen has something to submit. */
  onSubmit?: () => void
  /** Change this to focus the field and put the caret at the end (a screen's pre-filled draft). */
  focusKey?: number | string
}) {
  const [caret, setCaret] = useState(0)
  const [dismissed, setDismissed] = useState(false)
  const [active, setActive] = useState(0)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const lastFocus = useRef(focusKey)

  const query = dismissed ? null : mentionQueryAt(value, caret)
  const mention = useMentionTargets(projectId, query?.query ?? '', query !== null && !!projectId)

  useEffect(() => {
    setActive(0)
  }, [mention.targets])

  useEffect(() => {
    if (focusKey === undefined || focusKey === lastFocus.current) return
    lastFocus.current = focusKey
    const node = inputRef.current
    if (!node) return
    node.focus()
    const end = node.value.length
    node.setSelectionRange(end, end)
    setCaret(end)
  }, [focusKey])

  const change = (next: string, nextCaret: number): void => {
    setCaret(nextCaret)
    setDismissed(false)
    onChange(next, nextCaret)
  }

  const pick = (target: MentionTarget): void => {
    if (!query) return
    const marker = mentionMarker({ kind: target.kind, id: target.id, label: target.label })
    const before = value.slice(0, query.start)
    const after = value.slice(caret)
    const next = `${before}${marker} ${after}`
    const position = before.length + marker.length + 1
    setDismissed(true)
    onChange(next, position)
    setCaret(position)
    requestAnimationFrame(() => {
      const node = inputRef.current
      if (!node) return
      node.focus()
      node.setSelectionRange(position, position)
    })
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (query && mention.targets.length > 0) {
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        setActive((current) => (current + 1) % mention.targets.length)
        return
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault()
        setActive(
          (current) => (current - 1 + mention.targets.length) % mention.targets.length
        )
        return
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        event.preventDefault()
        pick(mention.targets[active])
        return
      }
      if (event.key === 'Escape') {
        setDismissed(true)
        return
      }
    }
    if (event.key === 'Enter' && !event.shiftKey && onSubmit) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="mention-field">
      {query && projectId ? (
        <MentionPicker
          targets={mention.targets}
          loading={mention.loading}
          active={active}
          error={mention.error}
          title={pickerTitle}
          onHover={setActive}
          onPick={pick}
        />
      ) : null}

      <textarea
        ref={inputRef}
        className={className}
        value={value}
        placeholder={placeholder}
        rows={rows}
        maxLength={maxLength}
        onChange={(event) => change(event.target.value, event.target.selectionStart ?? 0)}
        onKeyDown={onKeyDown}
        onClick={(event) => setCaret(event.currentTarget.selectionStart ?? 0)}
        onKeyUp={(event) => setCaret(event.currentTarget.selectionStart ?? 0)}
      />
    </div>
  )
}

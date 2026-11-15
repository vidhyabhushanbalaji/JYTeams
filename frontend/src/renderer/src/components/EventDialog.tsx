/**
 * Add or edit an event.
 *
 * An all-day event is pinned to UTC midnight so its day is the day that was picked in every
 * timezone; a timed event is sent with the machine's offset, so 14:00 means 14:00 here.
 */

import { useEffect, useState } from 'react'

import type { CalendarEvent, CalendarEventInput, CalendarEventPatch } from '@shared/types'

import { Dialog, Field } from './primitives'
import { MentionTextarea } from './MentionTextarea'

const pad = (value: number): string => `${value}`.padStart(2, '0')

const localDate = (iso: string): string => {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  return `${moment.getFullYear()}-${pad(moment.getMonth() + 1)}-${pad(moment.getDate())}`
}

const localTime = (iso: string): string => {
  const moment = new Date(iso)
  if (Number.isNaN(moment.getTime())) return ''
  return `${pad(moment.getHours())}:${pad(moment.getMinutes())}`
}

export function EventDialog({
  open,
  day,
  projectId,
  projectName,
  event,
  busy,
  onClose,
  onSave,
  onDelete
}: {
  open: boolean
  /** The day the dialog opens on (`YYYY-MM-DD`). */
  day: string
  /** The project the event belongs to; null makes it a personal event. */
  projectId: string | null
  projectName: string
  /** The event being edited, or null when adding one. */
  event: CalendarEvent | null
  busy: boolean
  onClose: () => void
  onSave: (input: CalendarEventInput | CalendarEventPatch) => Promise<void>
  onDelete: () => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [notes, setNotes] = useState('')
  const [date, setDate] = useState(day)
  const [time, setTime] = useState('09:00')
  const [endTime, setEndTime] = useState('')
  const [allDay, setAllDay] = useState(false)

  useEffect(() => {
    if (!open) return
    if (event) {
      setTitle(event.title)
      setNotes(event.notes)
      // An all-day event is stored at UTC midnight, so its day is the date prefix in any timezone.
      setDate(event.all_day ? event.starts_at.slice(0, 10) : localDate(event.starts_at))
      setAllDay(event.all_day)
      setTime(event.all_day ? '09:00' : localTime(event.starts_at))
      setEndTime(event.ends_at && !event.all_day ? localTime(event.ends_at) : '')
    } else {
      setTitle('')
      setNotes('')
      setDate(day)
      setTime('09:00')
      setEndTime('')
      setAllDay(false)
    }
  }, [open, event, day])

  const timestamps = (): { startsAt: string; endsAt: string | null } => {
    if (allDay) return { startsAt: `${date}T00:00:00Z`, endsAt: null }
    const start = new Date(`${date}T${time || '09:00'}:00`)
    const end = endTime ? new Date(`${date}T${endTime}:00`) : null
    return {
      startsAt: start.toISOString(),
      endsAt: end && end > start ? end.toISOString() : null
    }
  }

  const save = async (): Promise<void> => {
    const text = title.trim()
    if (!text) return
    const { startsAt, endsAt } = timestamps()
    if (event) {
      await onSave({ title: text, notes, startsAt, endsAt, allDay })
    } else {
      await onSave({ projectId, title: text, notes, startsAt, endsAt, allDay })
    }
  }

  // A project event keeps its scope when edited from the merged calendar.
  const belongsToProject = event ? Boolean(event.project_id) : Boolean(projectId)
  const where = event?.project_name || projectName

  return (
    <Dialog
      open={open}
      title={event ? 'Edit event' : 'Add an event'}
      subtitle={
        belongsToProject
          ? `On ${where}'s calendar — everyone in the project sees it.`
          : 'On your calendar — only you see it.'
      }
      onClose={onClose}
      footer={
        <>
          {event ? (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void onDelete()}
              disabled={busy}
            >
              Delete
            </button>
          ) : null}
          <span className="spacer" />
          <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={() => void save()}
            disabled={busy || !title.trim()}
          >
            {event ? 'Save' : 'Add event'}
          </button>
        </>
      }
    >
      <Field label="Title">
        <input
          className="field__input"
          value={title}
          onChange={(input) => setTitle(input.target.value)}
          maxLength={200}
          placeholder="Design review"
        />
      </Field>

      <div className="cal-form__row">
        <Field label="Day">
          <input
            className="field__input"
            type="date"
            value={date}
            onChange={(input) => setDate(input.target.value)}
          />
        </Field>
        <label className="field field--inline">
          <input
            type="checkbox"
            checked={allDay}
            onChange={(input) => setAllDay(input.target.checked)}
          />
          <span className="field__label">All day</span>
        </label>
      </div>

      {allDay ? null : (
        <div className="cal-form__row">
          <Field label="Starts">
            <input
              className="field__input"
              type="time"
              value={time}
              onChange={(input) => setTime(input.target.value)}
            />
          </Field>
          <Field label="Ends" hint="Optional">
            <input
              className="field__input"
              type="time"
              value={endTime}
              onChange={(input) => setEndTime(input.target.value)}
            />
          </Field>
        </div>
      )}

      <Field
        label="Notes"
        hint={belongsToProject ? 'Type @ to mention a document, folder or ticket' : 'Optional'}
      >
        <MentionTextarea
          projectId={belongsToProject ? (event?.project_id ?? projectId) : null}
          value={notes}
          onChange={(next) => setNotes(next)}
          rows={3}
          maxLength={2_000}
          placeholder={
            belongsToProject
              ? 'What is this about? Type @ to mention a document, folder or ticket.'
              : 'What is this about?'
          }
          pickerTitle="Mention a document, a folder or a ticket"
          className="field__input field__input--area"
        />
      </Field>
    </Dialog>
  )
}

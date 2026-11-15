/**
 * The calendar page: one calendar per project, plus the individual one that merges every project
 * the caller is in.
 *
 * Ticket deadlines are drawn from the tickets themselves (the backend reads them), so a deadline is
 * never stale and a completed ticket stops appearing. Pressing a deadline opens its ticket.
 */

import { useEffect, useMemo, useState } from 'react'

import type {
  CalendarEvent,
  CalendarEventInput,
  CalendarEventPatch,
  CalendarItem,
  CalendarMention,
  Member
} from '@shared/types'

import {
  addMonths,
  isoDay,
  isOverdue,
  itemLabel,
  sortItems,
  timeLabel
} from '../lib/calendar'
import { mentionDraft, mentionIcon, mentionOpenHint, plainBody } from '../lib/chat'
import { describeError } from '../lib/errors'
import type { GraphFocus } from '../lib/graphFocus'
import { STATUS_LABEL } from '../lib/tickets'
import { useCalendar, type CalendarScope } from '../state/useCalendar'
import { useProjects } from '../state/useProjects'
import { CalendarMonth } from './CalendarMonth'
import { EventDialog } from './EventDialog'
import { ErrorBox, Spinner } from './primitives'

const today = new Date()

const parseDay = (iso: string | null | undefined): Date | null => {
  if (!iso) return null
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

const asEvent = (item: CalendarItem): CalendarEvent => ({
  id: item.id,
  project_id: item.project_id,
  project_name: item.project_name,
  title: item.title,
  notes: item.notes,
  starts_at: item.starts_at ?? `${item.day}T00:00:00Z`,
  ends_at: item.ends_at,
  all_day: item.all_day,
  created_by: item.created_by,
  created_at: null,
  updated_at: null,
  mentions: item.mentions
})

const mentionLabel = (mention: CalendarMention): string =>
  mention.kind === 'ticket' && mention.ticket_number !== null
    ? `#${mention.ticket_number} ${mention.label}`
    : mention.label

export function CalendarScreen({
  member,
  initialProjectId,
  initialDay,
  onOpenTicket,
  onOpenProject,
  onOpenChat,
  notify
}: {
  member: Member
  /** A ticket or a chat mention asked for this project's calendar. */
  initialProjectId?: string | null
  /** The day to reveal (`YYYY-MM-DD`), when another screen sent us to an event. */
  initialDay?: string | null
  onOpenTicket: (projectId: string, ticketId: string) => void
  onOpenProject: (projectId: string, focus: GraphFocus) => void
  /** Start a chat message that mentions an event. */
  onOpenChat: (projectId: string, draft: string) => void
  notify: (message: string, tone?: 'info' | 'error') => void
}) {
  const { projects } = useProjects()
  const anchor = parseDay(initialDay) ?? today
  const [scope, setScope] = useState<CalendarScope>(
    initialProjectId ? { kind: 'project', projectId: initialProjectId } : { kind: 'personal' }
  )
  const [month, setMonth] = useState({ year: anchor.getFullYear(), month: anchor.getMonth() })
  const [selectedDay, setSelectedDay] = useState(initialDay ?? isoDay(today))
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CalendarEvent | null>(null)
  const [busy, setBusy] = useState(false)

  const calendar = useCalendar(scope, month.year, month.month)
  const items = calendar.range?.items ?? []

  useEffect(() => {
    if (initialProjectId) setScope({ kind: 'project', projectId: initialProjectId })
  }, [initialProjectId])

  useEffect(() => {
    const revealed = parseDay(initialDay)
    if (!revealed) return
    setMonth({ year: revealed.getFullYear(), month: revealed.getMonth() })
  }, [initialDay])

  useEffect(() => {
    const revealed = parseDay(initialDay)
    if (revealed && month.year === revealed.getFullYear() && month.month === revealed.getMonth()) {
      setSelectedDay(isoDay(revealed))
      return
    }
    const now = new Date()
    const isCurrentMonth = month.year === now.getFullYear() && month.month === now.getMonth()
    const monthStart = `${month.year}-${`${month.month + 1}`.padStart(2, '0')}-01`
    setSelectedDay(isCurrentMonth ? isoDay(now) : monthStart)
  }, [month, scope, initialDay])

  const dayItems = useMemo(
    () => sortItems(items.filter((item) => item.day === selectedDay)),
    [items, selectedDay]
  )

  const monthLabel = new Date(month.year, month.month, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric'
  })

  const scopeProjectId = scope.kind === 'project' ? scope.projectId ?? null : null
  const scopeProjectName =
    projects.find((project) => project.id === scopeProjectId)?.name ?? 'this project'

  const move = (delta: number): void => setMonth((current) => addMonths(current.year, current.month, delta))

  const openCreate = (): void => {
    setEditing(null)
    setDialogOpen(true)
  }

  const save = async (input: CalendarEventInput | CalendarEventPatch): Promise<void> => {
    setBusy(true)
    const result = editing
      ? await window.jyteams.calendar.update(editing.id, input as CalendarEventPatch)
      : await window.jyteams.calendar.create(input as CalendarEventInput)
    setBusy(false)
    if (!result.ok) {
      notify(describeError(result.error), 'error')
      return
    }
    notify(editing ? 'Event updated.' : 'Event added.')
    setDialogOpen(false)
    setEditing(null)
    await calendar.reload()
  }

  const remove = async (): Promise<void> => {
    if (!editing) return
    setBusy(true)
    const result = await window.jyteams.calendar.remove(editing.id)
    setBusy(false)
    if (!result.ok) {
      notify(describeError(result.error), 'error')
      return
    }
    notify('Event removed.')
    setDialogOpen(false)
    setEditing(null)
    await calendar.reload()
  }

  /** A chip in an event's notes opens the document, folder or ticket it points at. */
  const openMention = (item: CalendarItem, mention: CalendarMention): void => {
    if (!item.project_id) return
    if (mention.kind === 'ticket') {
      onOpenTicket(item.project_id, mention.id)
      return
    }
    if (mention.kind === 'directory') {
      onOpenProject(item.project_id, {
        kind: 'directory',
        label: mention.label,
        directoryId: mention.id,
        directoryPath: mention.path
      })
      return
    }
    onOpenProject(item.project_id, {
      kind: 'files',
      label: mention.label,
      targets: [
        {
          fileId: mention.id,
          directoryPath: mention.directory_path,
          name: mention.label
        }
      ],
      entryFileId: mention.id
    })
  }

  /** Start the project's chat on this event — the composer arrives with its mention in place. */
  const discuss = (item: CalendarItem): void => {
    if (!item.project_id) return
    onOpenChat(
      item.project_id,
      mentionDraft({ kind: 'event', id: item.id, label: item.title, ticket_number: null })
    )
  }

  return (
    <div className="screen screen--wide">
      <div className="screen__inner">
        <header className="screen__head">
          <div>
            <h1 className="screen__title">Calendar</h1>
            <p className="screen__lede">
              {member.display_name}, this is{' '}
              {scope.kind === 'personal'
                ? 'your merged calendar'
                : `${scopeProjectName}'s calendar`}
              . Ticket deadlines appear on their own, and a finished ticket drops off. An event’s
              notes can mention a document, folder or ticket with @, and{' '}
              <strong>Message in chat</strong> starts a discussion about the event in the project’s
              chat.
            </p>
          </div>
          <div className="screen__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void calendar.reload()}
            >
              Refresh
            </button>
            <button type="button" className="btn btn--primary" onClick={openCreate}>
              Add event
            </button>
          </div>
        </header>

        <div className="cal-scopes">
          <button
            type="button"
            className={`cal-scope${scope.kind === 'personal' ? ' cal-scope--active' : ''}`}
            onClick={() => setScope({ kind: 'personal' })}
          >
            My calendar
          </button>
          {projects.map((project) => (
            <button
              key={project.id}
              type="button"
              className={`cal-scope${
                scope.kind === 'project' && scope.projectId === project.id
                  ? ' cal-scope--active'
                  : ''
              }`}
              onClick={() => setScope({ kind: 'project', projectId: project.id })}
            >
              {project.name}
            </button>
          ))}
        </div>

        <div className="cal-bar">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => move(-1)}
            aria-label="Previous month"
          >
            {'\u2039'}
          </button>
          <span className="cal-bar__month">{monthLabel}</span>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => move(1)}
            aria-label="Next month"
          >
            {'\u203a'}
          </button>
          <span className="cal-bar__grow" />
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              const now = new Date()
              setMonth({ year: now.getFullYear(), month: now.getMonth() })
            }}
          >
            Today
          </button>
        </div>

        {calendar.status === 'loading' && !calendar.range ? (
          <div className="empty">
            <Spinner label="Loading the calendar" />
          </div>
        ) : null}

        {calendar.status === 'error' && calendar.error ? (
          <ErrorBox
            title="This calendar could not be loaded"
            detail={describeError(calendar.error)}
          >
            <div style={{ marginTop: 10 }}>
              <button type="button" className="btn btn--sm" onClick={() => void calendar.reload()}>
                Try again
              </button>
            </div>
          </ErrorBox>
        ) : null}

        {calendar.range ? (
          <div className="cal-layout">
            <div className="cal-layout__grid">
              <CalendarMonth
                grid={calendar.grid}
                items={items}
                selectedDay={selectedDay}
                onSelectDay={setSelectedDay}
              />
            </div>

            <aside className="cal-layout__day">
              <span className="side__label">
                {selectedDay === isoDay(today) ? 'Today' : selectedDay}
              </span>

              {dayItems.length === 0 ? (
                <p className="side__text">Nothing on this day.</p>
              ) : (
                <ul className="cal-day-list">
                  {dayItems.map((item) => (
                    <li
                      key={`${item.kind}-${item.id}`}
                      className={`cal-day-item cal-day-item--${item.kind}${
                        isOverdue(item) ? ' cal-day-item--overdue' : ''
                      }`}
                    >
                      <span className="cal-day-item__time">{timeLabel(item)}</span>
                      <span className="cal-day-item__body">
                        <span className="cal-day-item__title">{itemLabel(item)}</span>
                        <span className="cal-day-item__meta">
                          {item.kind === 'deadline'
                            ? [
                                item.project_name,
                                item.assignee?.display_name,
                                item.status ? STATUS_LABEL[item.status] : ''
                              ]
                                .filter(Boolean)
                                .join(' · ')
                            : [
                                scope.kind === 'personal'
                                  ? item.project_name || 'Personal'
                                  : '',
                                item.created_by?.display_name ?? ''
                              ]
                                .filter(Boolean)
                                .join(' · ')}
                        </span>
                        {item.notes ? (
                          <span className="cal-day-item__notes">{plainBody(item.notes)}</span>
                        ) : null}
                        {item.mentions.length > 0 ? (
                          <span className="cal-day-item__mentions">
                            {item.mentions.map((mention) => (
                              <button
                                key={`${mention.kind}-${mention.id}`}
                                type="button"
                                className={`mention-chip mention-chip--${mention.kind}`}
                                title={mentionOpenHint(mention.kind)}
                                onClick={() => openMention(item, mention)}
                              >
                                <span aria-hidden="true">{mentionIcon(mention.kind)}</span>
                                {mentionLabel(mention)}
                              </button>
                            ))}
                          </span>
                        ) : null}
                      </span>
                      <span className="cal-day-item__actions">
                        {item.kind === 'deadline' && item.ticket_id && item.project_id ? (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() =>
                              onOpenTicket(item.project_id as string, item.ticket_id as string)
                            }
                          >
                            Open ticket
                          </button>
                        ) : null}
                        {item.kind === 'event' && item.project_id ? (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => discuss(item)}
                            title="Open the project chat with this event mentioned"
                          >
                            Message in chat
                          </button>
                        ) : null}
                        {item.editable ? (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => {
                              setEditing(asEvent(item))
                              setDialogOpen(true)
                            }}
                          >
                            Edit
                          </button>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </aside>
          </div>
        ) : null}
      </div>

      <EventDialog
        open={dialogOpen}
        day={selectedDay}
        projectId={scopeProjectId}
        projectName={scopeProjectName}
        event={editing}
        busy={busy}
        onClose={() => {
          setDialogOpen(false)
          setEditing(null)
        }}
        onSave={save}
        onDelete={remove}
      />
    </div>
  )
}

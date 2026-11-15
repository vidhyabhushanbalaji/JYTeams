/**
 * The tickets page: my to-do list on the left, one ticket (or the project's updates) on the
 * right. Reached from the rail.
 *
 * A ticket's files come from the backend's cached search, so selecting a ticket is cheap; the
 * only expensive action is Refresh. Pressing a file hands the project graph a set to highlight.
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import type { ApiResult, Member, Project, Ticket, TicketStatus } from '@shared/types'

import { describeError } from '../lib/errors'
import {
  eventText,
  groupByProject,
  PRIORITY_LABEL,
  relativeTime,
  STATUS_LABEL,
  ticketKey
} from '../lib/tickets'
import { mentionDraft } from '../lib/chat'
import type { GraphFocus } from '../lib/graphFocus'
import { useActivity } from '../state/useActivity'
import { useProjects } from '../state/useProjects'
import { useTicketCalendar } from '../state/useTicketCalendar'
import { useTicketDetail } from '../state/useTicketDetail'
import { useTickets } from '../state/useTickets'
import { AddDocumentFlow } from './AddDocumentFlow'
import { AttachFileDialog } from './AttachFileDialog'
import { ShareProjectDialog } from './ShareProjectDialog'
import { TicketComposer } from './TicketComposer'
import { TicketDetailPanel } from './TicketDetailPanel'
import { Empty, ErrorBox, Spinner } from './primitives'

const STATUSES: TicketStatus[] = ['todo', 'in_progress', 'done']

export function TicketsScreen({
  member,
  members,
  initialTicketId,
  initialProjectId,
  onOpenProject,
  onOpenChat,
  onOpenCalendar,
  onSwitchUser,
  notify
}: {
  member: Member
  /** Every name that has signed in — the share dialog offers the ones not yet on a project. */
  members: Member[]
  /** A ticket a chat mention or a calendar deadline asked to open. */
  initialTicketId?: string | null
  /** The project that ticket belongs to, so the list is filtered to it first. */
  initialProjectId?: string | null
  onOpenProject: (projectId: string, focus: GraphFocus) => void
  /** Start the project chat with a ticket mentioned. */
  onOpenChat: (projectId: string, draft: string) => void
  /** Open the calendar on the day an event mentioning this ticket sits on. */
  onOpenCalendar: (projectId: string, day: string) => void
  onSwitchUser: () => void
  notify: (message: string, tone?: 'info' | 'error') => void
}) {
  const { projects } = useProjects()
  const [scope, setScope] = useState<'mine' | 'project'>('mine')
  const [projectId, setProjectId] = useState('')
  const [statusFilter, setStatusFilter] = useState<TicketStatus | ''>('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [panel, setPanel] = useState<'ticket' | 'updates'>('ticket')
  const [revision, setRevision] = useState(0)
  const [busy, setBusy] = useState(false)
  const [composerOpen, setComposerOpen] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [attachOpen, setAttachOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const appliedInitial = useRef(false)
  const skipReset = useRef(true)

  const {
    tickets,
    loading,
    error,
    reload: reloadTickets
  } = useTickets(
    { scope, projectId: projectId || undefined, status: statusFilter || null },
    true
  )
  const { detail, loading: detailLoading, error: detailError, reload: reloadDetail } =
    useTicketDetail(selectedId)
  const calendar = useTicketCalendar(detail?.project_id ?? null, selectedId)
  const { events, loading: feedLoading, error: feedError } = useActivity(
    { projectId: projectId || undefined },
    true,
    revision
  )

  useEffect(() => {
    if (!initialTicketId || appliedInitial.current) return
    appliedInitial.current = true
    if (initialProjectId) {
      setScope('project')
      setProjectId(initialProjectId)
    }
    setSelectedId(initialTicketId)
    skipReset.current = true
  }, [initialTicketId, initialProjectId])

  useEffect(() => {
    if (skipReset.current) {
      skipReset.current = false
      return
    }
    setSelectedId(null)
  }, [scope, projectId, statusFilter])

  const groups = useMemo(() => groupByProject(tickets), [tickets])
  const selectedProject = useMemo<Project | null>(
    () => projects.find((project) => project.id === detail?.project_id) ?? null,
    [projects, detail]
  )

  const runWrite = async <T,>(
    work: () => Promise<ApiResult<T>>,
    message?: string
  ): Promise<T | null> => {
    setBusy(true)
    const result = await work()
    setBusy(false)
    if (!result.ok) {
      notify(describeError(result.error), 'error')
      return null
    }
    if (message) notify(message)
    setRevision((value) => value + 1)
    await reloadTickets()
    await reloadDetail()
    await calendar.reload()
    return result.data
  }

  const selected = detail
  const attachedIds = new Set(selected?.files.attached.map((file) => file.file_id) ?? [])

  const openGraph = (args: {
    label: string
    targets: { fileId: string; directoryPath: string; name: string }[]
    entryFileId: string
  }): void => {
    if (!selected) return
    onOpenProject(selected.project_id, {
      kind: 'files',
      label: args.label,
      targets: args.targets,
      entryFileId: args.entryFileId
    })
  }

  return (
    <div className="screen screen--wide">
      <div className="screen__inner">
        <header className="screen__head">
          <div>
            <h1 className="screen__title">Tickets</h1>
            <p className="screen__lede">
              Your tasks across every project you can see, {member.display_name}. Opening a ticket
              finds the documents it is about — no model is called — and shows the calendar events
              whose notes mention it. <strong>Discuss in chat</strong> starts a message about the
              ticket in its project’s chat.
            </p>
          </div>
          <div className="screen__actions">
            <button type="button" className="btn btn--ghost btn--sm" onClick={onSwitchUser}>
              Switch user
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => {
                setRevision((value) => value + 1)
                void reloadTickets()
                void reloadDetail()
                void calendar.reload()
              }}
            >
              Refresh
            </button>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => setComposerOpen(true)}
              disabled={projects.length === 0}
              title={projects.length === 0 ? 'Create a project first' : undefined}
            >
              New ticket
            </button>
          </div>
        </header>

        <div className="ticket-filters">
          <div className="ticket-filters__group">
            <button
              type="button"
              className={`chip chip--button${scope === 'mine' ? ' badge--ink' : ''}`}
              onClick={() => setScope('mine')}
            >
              My tasks
            </button>
            <button
              type="button"
              className={`chip chip--button${scope === 'project' ? ' badge--ink' : ''}`}
              onClick={() => {
                setScope('project')
                if (!projectId && projects[0]) setProjectId(projects[0].id)
              }}
            >
              Everyone on a project
            </button>
          </div>

          <label className="ticket-filters__field">
            <span className="field__label">Project</span>
            <select
              className="field__input field__input--inline"
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
            >
              {scope === 'mine' ? <option value="">All my projects</option> : null}
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                  {project.role === 'member' ? ' (shared)' : ''}
                </option>
              ))}
            </select>
          </label>

          <label className="ticket-filters__field">
            <span className="field__label">Status</span>
            <select
              className="field__input field__input--inline"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as TicketStatus | '')}
            >
              <option value="">Any</option>
              {STATUSES.map((value) => (
                <option key={value} value={value}>
                  {STATUS_LABEL[value]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="tickets">
          <section className="tickets__list">
            {loading ? (
              <div className="empty">
                <Spinner label="Loading tickets" />
              </div>
            ) : null}

            {!loading && error ? (
              <ErrorBox title="Tickets could not be loaded" detail={describeError(error)}>
                <button type="button" className="btn btn--sm" onClick={() => void reloadTickets()}>
                  Try again
                </button>
              </ErrorBox>
            ) : null}

            {!loading && !error && tickets.length === 0 ? (
              <Empty
                title={scope === 'mine' ? 'Nothing assigned to you' : 'No tickets on this project'}
                text="A ticket is a task on one project. Create one, or ask a teammate to assign you theirs."
              >
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => setComposerOpen(true)}
                  disabled={projects.length === 0}
                >
                  New ticket
                </button>
              </Empty>
            ) : null}

            {groups.map((group) => (
              <div key={group.projectId} className="ticket-group">
                <div className="ticket-group__head">
                  <span className="side__label">{group.projectName}</span>
                  <span className="ticket-group__count">{group.tickets.length}</span>
                </div>
                <ul className="ticket-list">
                  {group.tickets.map((ticket) => (
                    <li key={ticket.id}>
                      <button
                        type="button"
                        className={`ticket-row${ticket.id === selectedId ? ' ticket-row--active' : ''}${ticket.status === 'done' ? ' ticket-row--done' : ''}`}
                        onClick={() => {
                          setSelectedId(ticket.id)
                          setPanel('ticket')
                        }}
                      >
                        <span className={`ticket-row__dot ticket-row__dot--${ticket.priority}`} />
                        <span className="ticket-row__body">
                          <span className="ticket-row__title">
                            <span className="ticket-row__key">{ticketKey(ticket)}</span>
                            {ticket.title}
                          </span>
                          <span className="ticket-row__meta">
                            {STATUS_LABEL[ticket.status]}
                            {' · '}
                            {PRIORITY_LABEL[ticket.priority]} priority
                            {ticket.due_date ? ` · due ${ticket.due_date.slice(0, 10)}` : ''}
                            {ticket.assignee ? ` · ${ticket.assignee.display_name}` : ''}
                          </span>
                        </span>
                        <span className="ticket-row__side">
                          {ticket.attachment_count > 0 ? (
                            <span className="ticket-row__badge">
                              {ticket.attachment_count} files
                            </span>
                          ) : null}
                          {ticket.comment_count > 0 ? (
                            <span className="ticket-row__badge">
                              {ticket.comment_count} comments
                            </span>
                          ) : null}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>

          <aside className="tickets__side">
            <div className="ticket-tabs">
              <button
                type="button"
                className={`ticket-tab${panel === 'ticket' ? ' ticket-tab--active' : ''}`}
                onClick={() => setPanel('ticket')}
              >
                Ticket
              </button>
              <button
                type="button"
                className={`ticket-tab${panel === 'updates' ? ' ticket-tab--active' : ''}`}
                onClick={() => setPanel('updates')}
              >
                Changes and updates
              </button>
            </div>

            {panel === 'ticket' ? (
              <TicketDetailPanel
                detail={detail}
                loading={detailLoading}
                error={detailError}
                busy={busy}
                onToggleComplete={async (done) => {
                  if (!selected) return
                  await runWrite(
                    () => window.jyteams.tickets.setStatus(selected.id, done ? 'done' : 'todo'),
                    done ? `Completed ${ticketKey(selected)}.` : `Reopened ${ticketKey(selected)}.`
                  )
                }}
                onSetStatus={async (status) => {
                  if (!selected) return
                  await runWrite(
                    () => window.jyteams.tickets.setStatus(selected.id, status),
                    `${ticketKey(selected)} is now ${STATUS_LABEL[status].toLowerCase()}.`
                  )
                }}
                onPatch={async (patch) => {
                  if (!selected) return
                  await runWrite(
                    () => window.jyteams.tickets.update(selected.id, patch),
                    'Ticket updated.'
                  )
                }}
                onComment={async (body) => {
                  if (!selected) return
                  await runWrite(() => window.jyteams.tickets.comment(selected.id, body))
                }}
                onRefreshFiles={async () => {
                  setBusy(true)
                  await reloadDetail(true)
                  setBusy(false)
                }}
                onOpenGraph={openGraph}
                onUploadFile={() => setUploadOpen(true)}
                onAttachExisting={() => setAttachOpen(true)}
                onDetach={async (fileId) => {
                  if (!selected) return
                  await runWrite(
                    () => window.jyteams.tickets.detach(selected.id, fileId),
                    'Document taken off the ticket.'
                  )
                }}
                onShareProject={() => setShareOpen(true)}
                onDiscuss={() => {
                  if (!selected) return
                  onOpenChat(
                    selected.project_id,
                    mentionDraft({
                      kind: 'ticket',
                      id: selected.id,
                      label: selected.title,
                      ticket_number: selected.number
                    })
                  )
                }}
                calendarEvents={calendar.events}
                calendarLoading={calendar.loading}
                calendarError={calendar.error}
                onOpenCalendar={(day) => {
                  if (selected) onOpenCalendar(selected.project_id, day)
                }}
              />
            ) : (
              <div className="feed">
                {feedLoading ? (
                  <p className="side__empty">
                    <Spinner label="Loading updates" /> Reading the feed.
                  </p>
                ) : null}
                {feedError ? (
                  <div className="notice notice--error">{describeError(feedError)}</div>
                ) : null}
                {!feedLoading && events.length === 0 ? (
                  <p className="side__empty">
                    Nothing has happened yet. Uploads, added files and completed tickets show up
                    here.
                  </p>
                ) : null}
                <ul className="feed__list">
                  {events.map((event) => (
                    <li key={event.id} className="feed__row">
                      <span className="feed__text">{eventText(event)}</span>
                      <span className="feed__time">{relativeTime(event.created_at)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </aside>
        </div>
      </div>


      <TicketComposer
        open={composerOpen}
        projects={projects}
        onClose={() => setComposerOpen(false)}
        onCreated={(ticket: Ticket) => {
          setSelectedId(ticket.id)
          setPanel('ticket')
          setRevision((value) => value + 1)
          void reloadTickets()
          notify(`${ticketKey(ticket)} created.`)
        }}
      />

      {selected ? (
        <AddDocumentFlow
          open={uploadOpen}
          projectId={selected.project_id}
          context={`${selected.title}\n${selected.description}`.slice(0, 500)}
          onClose={() => setUploadOpen(false)}
          onPlaced={(result) => {
            void runWrite(
              () => window.jyteams.tickets.attach(selected.id, result.file.id, 'upload'),
              `Added ${result.file.name} and put it on ${ticketKey(selected)}.`
            ).then(() => setUploadOpen(false))
          }}
        />
      ) : null}

      {selected ? (
        <AttachFileDialog
          open={attachOpen}
          projectId={selected.project_id}
          attachedIds={attachedIds}
          onClose={() => setAttachOpen(false)}
          onAttach={async (fileId) => {
            await runWrite(() =>
              window.jyteams.tickets.attach(selected.id, fileId, 'existing')
            )
          }}
        />
      ) : null}

      <ShareProjectDialog
        open={shareOpen}
        project={selectedProject}
        members={members}
        currentMemberId={member.id}
        onClose={() => setShareOpen(false)}
      />
    </div>
  )
}


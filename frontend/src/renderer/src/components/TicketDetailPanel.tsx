/**
 * A ticket's detail: the fields, the completion box, the files area and the comments.
 *
 * The files come from the cached Graph AI Search result the backend keeps on the ticket, so
 * opening this panel again costs no search; pressing one opens the project graph at that
 * document, with every other match highlighted.
 */

import { useEffect, useState } from 'react'

import type { ApiError, TicketDetail, TicketPriority, TicketStatus } from '@shared/types'

import { describeError } from '../lib/errors'
import { humanBytes, scoreText, shortDate } from '../lib/format'
import { dueLabel, matchTargets, STATUS_LABEL, ticketKey } from '../lib/tickets'
import { Spinner } from './primitives'

const STATUSES: TicketStatus[] = ['todo', 'in_progress', 'done']
const PRIORITIES: TicketPriority[] = ['low', 'medium', 'high']

export interface OpenGraphArgs {
  label: string
  targets: { fileId: string; directoryPath: string; name: string }[]
  entryFileId: string
}

export interface TicketPanelProps {
  detail: TicketDetail | null
  loading: boolean
  error: ApiError | null
  busy: boolean
  onToggleComplete: (done: boolean) => Promise<void>
  onSetStatus: (status: TicketStatus) => Promise<void>
  onPatch: (patch: {
    title?: string
    description?: string
    priority?: TicketPriority
    dueDate?: string | null
    labels?: string[]
  }) => Promise<void>
  onComment: (body: string) => Promise<void>
  onRefreshFiles: () => Promise<void>
  onOpenGraph: (args: OpenGraphArgs) => void
  onUploadFile: () => void
  onAttachExisting: () => void
  onDetach: (fileId: string) => Promise<void>
  onShareProject: () => void
}

export function TicketDetailPanel(props: TicketPanelProps) {
  const { detail, loading, error, busy, onPatch, onOpenGraph } = props
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [dueDate, setDueDate] = useState('')
  const [labels, setLabels] = useState('')
  const [comment, setComment] = useState('')

  useEffect(() => {
    setEditing(false)
    setComment('')
  }, [detail?.id])

  useEffect(() => {
    if (!detail || editing) return
    setTitle(detail.title)
    setDescription(detail.description)
    setPriority(detail.priority)
    setDueDate(detail.due_date ? detail.due_date.slice(0, 10) : '')
    setLabels(detail.labels.join(', '))
  }, [detail, editing])

  if (loading && !detail) {
    return (
      <div className="ticket-panel__state">
        <Spinner label="Opening the ticket" />
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="ticket-panel__state">
        <p className="side__text">
          {error ? describeError(error) : 'Pick a ticket to see it here.'}
        </p>
      </div>
    )
  }

  const files = detail.files
  const targets = matchTargets(files.attached, files.suggested)
  const label = `${ticketKey(detail)} ${detail.title}`
  const due = dueLabel(detail.due_date)
  const done = detail.status === 'done'

  const openAt = (fileId: string): void => {
    if (targets.length === 0) return
    onOpenGraph({ label, targets, entryFileId: fileId })
  }

  const save = async (): Promise<void> => {
    await onPatch({
      title: title.trim(),
      description,
      priority,
      dueDate: dueDate || null,
      labels: labels
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean)
    })
    setEditing(false)
  }

  return (
    <div className="ticket-panel">
      <header className="ticket-panel__head">
        <div className="ticket-panel__crumbs">
          <span className="ticket-chip">{detail.project_name || 'Project'}</span>
          <span className="ticket-panel__key">{ticketKey(detail)}</span>
          <span className="ticket-panel__status">{STATUS_LABEL[detail.status]}</span>
        </div>
        <div className="ticket-panel__head-actions">
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setEditing((value) => !value)}
          >
            {editing ? 'Cancel' : 'Edit'}
          </button>
          <button type="button" className="btn btn--ghost btn--sm" onClick={props.onShareProject}>
            Share project
          </button>
        </div>
      </header>

      {editing ? (
        <div className="ticket-form">
          <label className="field">
            <span className="field__label">Title</span>
            <input
              className="field__input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={200}
            />
          </label>
          <label className="field">
            <span className="field__label">Description</span>
            <textarea
              className="field__input field__input--area"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
            />
          </label>
          <div className="ticket-form__row">
            <label className="field">
              <span className="field__label">Priority</span>
              <select
                className="field__input"
                value={priority}
                onChange={(event) => setPriority(event.target.value as TicketPriority)}
              >
                {PRIORITIES.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="field__label">Due</span>
              <input
                type="date"
                className="field__input"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
              />
            </label>
          </div>
          <label className="field">
            <span className="field__label">Labels</span>
            <input
              className="field__input"
              value={labels}
              onChange={(event) => setLabels(event.target.value)}
              placeholder="auth, docs"
            />
          </label>
          <div className="ticket-form__actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void save()}
              disabled={busy || !title.trim()}
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <>
          <h2 className="ticket-panel__title">{detail.title}</h2>
          <p className="ticket-panel__description">
            {detail.description || 'No description yet. Add one and the file search gets sharper.'}
          </p>
        </>
      )}

      <div className="ticket-panel__meta">
        <label className="checkline">
          <input
            type="checkbox"
            checked={done}
            disabled={busy}
            onChange={(event) => void props.onToggleComplete(event.target.checked)}
          />
          <span>
            {done
              ? `Completed${detail.completed_by ? ` by ${detail.completed_by.display_name}` : ''}`
              : 'Mark complete'}
          </span>
        </label>

        <select
          className="field__input field__input--inline"
          value={detail.status}
          disabled={busy}
          onChange={(event) => void props.onSetStatus(event.target.value as TicketStatus)}
          aria-label="Status"
        >
          {STATUSES.map((value) => (
            <option key={value} value={value}>
              {STATUS_LABEL[value]}
            </option>
          ))}
        </select>

        <span className={`badge badge--${detail.priority}`}>{detail.priority}</span>
        {due.text ? (
          <span className={`badge${due.overdue ? ' badge--danger' : ''}`}>Due {due.text}</span>
        ) : null}
        <span className="ticket-panel__person">
          {detail.assignee ? `Assigned to ${detail.assignee.display_name}` : 'Unassigned'}
        </span>
        <span className="ticket-panel__person">Opened {shortDate(detail.created_at)}</span>
      </div>

      {detail.labels.length > 0 ? (
        <div className="chips">
          {detail.labels.map((text) => (
            <span key={text} className="chip chip--static">
              {text}
            </span>
          ))}
        </div>
      ) : null}

      <section className="ticket-files">
        <div className="ticket-files__head">
          <div>
            <span className="side__label">Files</span>
            <p className="ticket-files__hint">
              {files.cached_at
                ? `Found ${files.suggested.length} document${files.suggested.length === 1 ? '' : 's'} · as of ${shortDate(files.cached_at)}`
                : 'Not searched yet.'}
              {files.stale ? ' · the project changed since, refresh for accuracy' : ''}
            </p>
            {files.query ? (
              <p className="ticket-files__hint">Searching for “{files.query}”</p>
            ) : null}
          </div>
          <div className="ticket-files__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void props.onRefreshFiles()}
              disabled={busy}
            >
              {busy ? <Spinner label="Refreshing" /> : null}
              Refresh
            </button>
            <button type="button" className="btn btn--sm" onClick={props.onUploadFile}>
              Add file
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={props.onAttachExisting}
            >
              Attach existing
            </button>
          </div>
        </div>

        {files.reason ? <div className="notice notice--warn">{files.reason}</div> : null}

        {files.attached.length > 0 ? (
          <>
            <span className="ticket-files__group">On this ticket</span>
            <ul className="ticket-file-list">
              {files.attached.map((file) => (
                <li key={file.file_id} className="ticket-file ticket-file--attached">
                  <button
                    type="button"
                    className="ticket-file__open"
                    onClick={() => openAt(file.file_id)}
                  >
                    <span className="ticket-file__name">{file.name}</span>
                    <span className="ticket-file__path">
                      {file.directory_path || 'project root'} · {humanBytes(file.size_bytes)}
                      {file.added_by ? ` · ${file.added_by.display_name}` : ''}
                    </span>
                  </button>
                  <button
                    type="button"
                    className="btn btn--ghost btn--icon btn--sm"
                    onClick={() => void props.onDetach(file.file_id)}
                    title="Take this document off the ticket"
                    aria-label={`Take ${file.name} off the ticket`}
                  >
                    {'\u00d7'}
                  </button>
                </li>
              ))}
            </ul>
          </>
        ) : null}

        <span className="ticket-files__group">Suggested by search</span>
        {files.suggested.length === 0 ? (
          <p className="side__empty">
            {files.reason ??
              'No documents matched this ticket’s words. Refresh after adding files.'}
          </p>
        ) : (
          <ul className="ticket-file-list">
            {files.suggested.map((file) => (
              <li key={file.file_id} className="ticket-file">
                <button
                  type="button"
                  className="ticket-file__open"
                  onClick={() => openAt(file.file_id)}
                >
                  <span className="ticket-file__name">{file.name}</span>
                  <span className="ticket-file__path">
                    {file.directory_path || 'project root'} · match {scoreText(file.score)}
                  </span>
                  {file.matched_terms.length > 0 ? (
                    <span className="ticket-file__terms">
                      {file.matched_terms.slice(0, 6).join(' · ')}
                    </span>
                  ) : null}
                  {file.excerpt ? (
                    <span className="ticket-file__excerpt">{file.excerpt}</span>
                  ) : null}
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className="ticket-files__foot">
          Press a file to open the project graph at it; every other match stays highlighted.
        </p>
      </section>

      <section className="ticket-comments">
        <span className="side__label">Comments</span>
        {detail.comments.length === 0 ? (
          <p className="side__empty">No comments yet.</p>
        ) : (
          <ul className="comment-list">
            {detail.comments.map((item) => (
              <li key={item.id} className="comment">
                <span className="comment__meta">
                  {item.author?.display_name ?? 'Someone'} · {shortDate(item.created_at)}
                </span>
                <p className="comment__body">{item.body}</p>
              </li>
            ))}
          </ul>
        )}
        <form
          className="comment-form"
          onSubmit={(event) => {
            event.preventDefault()
            const body = comment.trim()
            if (!body) return
            void props.onComment(body).then(() => setComment(''))
          }}
        >
          <textarea
            className="field__input field__input--area"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Add a comment"
            rows={2}
            maxLength={4000}
          />
          <button type="submit" className="btn btn--sm" disabled={!comment.trim() || busy}>
            Comment
          </button>
        </form>
      </section>
    </div>
  )
}

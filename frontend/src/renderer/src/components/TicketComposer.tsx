/** Create a ticket. The reporter is whoever is signed in; the assignee defaults to them. */

import { useEffect, useState } from 'react'

import type { Project, ProjectMember, Ticket, TicketPriority } from '@shared/types'

import { describeError } from '../lib/errors'
import { Dialog, Spinner } from './primitives'

const PRIORITIES: TicketPriority[] = ['low', 'medium', 'high']

export function TicketComposer({
  open,
  projects,
  onClose,
  onCreated
}: {
  open: boolean
  projects: Project[]
  onClose: () => void
  onCreated: (ticket: Ticket) => void
}) {
  const [projectId, setProjectId] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assigneeId, setAssigneeId] = useState('')
  const [priority, setPriority] = useState<TicketPriority>('medium')
  const [dueDate, setDueDate] = useState('')
  const [labels, setLabels] = useState('')
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setProjectId(projects[0]?.id ?? '')
    setTitle('')
    setDescription('')
    setAssigneeId('')
    setPriority('medium')
    setDueDate('')
    setLabels('')
    setError(null)
  }, [open, projects])

  useEffect(() => {
    if (!open || !projectId) {
      setMembers([])
      return
    }
    let cancelled = false
    void window.jyteams.tickets.projectMembers(projectId).then((result) => {
      if (cancelled) return
      setMembers(result.ok ? result.data : [])
    })
    return () => {
      cancelled = true
    }
  }, [open, projectId])

  const submit = async (): Promise<void> => {
    if (!projectId || !title.trim()) return
    setSaving(true)
    setError(null)
    const result = await window.jyteams.tickets.create({
      projectId,
      title: title.trim(),
      description,
      assigneeId: assigneeId || null,
      priority,
      dueDate: dueDate || null,
      labels: labels
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean)
    })
    setSaving(false)
    if (result.ok) {
      onCreated(result.data)
      onClose()
    } else {
      setError(describeError(result.error))
    }
  }

  return (
    <Dialog
      open={open}
      title="New ticket"
      subtitle="A task on one project, assigned to one person."
      onClose={onClose}
      footer={
        <>
          <span className="spacer" />
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => void submit()}
            disabled={saving || !projectId || !title.trim()}
          >
            {saving ? <Spinner label="Creating" /> : null}
            Create ticket
          </button>
        </>
      }
    >
      <label className="field">
        <span className="field__label">Project</span>
        <select
          className="field__input"
          value={projectId}
          onChange={(event) => {
            setProjectId(event.target.value)
            setAssigneeId('')
          }}
        >
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span className="field__label">Title</span>
        <input
          className="field__input"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="e.g. Fix the login redirect"
          maxLength={200}
          autoFocus
        />
      </label>

      <label className="field">
        <span className="field__label">Description</span>
        <textarea
          className="field__input field__input--area"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={4}
          placeholder="What is wrong, or what needs doing? This text is what finds the project's files."
        />
      </label>

      <div className="ticket-form__row">
        <label className="field">
          <span className="field__label">Assignee</span>
          <select
            className="field__input"
            value={assigneeId}
            onChange={(event) => setAssigneeId(event.target.value)}
          >
            <option value="">Me</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.display_name}
              </option>
            ))}
          </select>
        </label>

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
      </div>

      <div className="ticket-form__row">
        <label className="field">
          <span className="field__label">Due date</span>
          <input
            type="date"
            className="field__input"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Labels</span>
          <input
            className="field__input"
            value={labels}
            onChange={(event) => setLabels(event.target.value)}
            placeholder="auth, docs"
          />
        </label>
      </div>

      {error ? <div className="notice notice--error">{error}</div> : null}
    </Dialog>
  )
}

/**
 * Share a project with another member, by name. Only the project's owner may add or remove,
 * which the backend enforces — the dialog just mirrors it.
 */

import { useEffect, useState } from 'react'

import type { Member, Project, ProjectMember } from '@shared/types'

import { describeError } from '../lib/errors'
import { Dialog, Spinner } from './primitives'

export function ShareProjectDialog({
  open,
  project,
  members,
  currentMemberId,
  onClose
}: {
  open: boolean
  project: Project | null
  members: Member[]
  currentMemberId: string
  onClose: () => void
}) {
  const [current, setCurrent] = useState<ProjectMember[]>([])
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !project) return
    setError(null)
    setBusyId(null)
    void window.jyteams.tickets.projectMembers(project.id).then((result) => {
      if (result.ok) setCurrent(result.data)
      else setError(describeError(result.error))
    })
  }, [open, project])

  const reload = async (): Promise<void> => {
    if (!project) return
    const result = await window.jyteams.tickets.projectMembers(project.id)
    if (result.ok) setCurrent(result.data)
    else setError(describeError(result.error))
  }

  const add = async (memberId: string): Promise<void> => {
    if (!project) return
    setBusyId(memberId)
    setError(null)
    const result = await window.jyteams.tickets.share(project.id, memberId)
    setBusyId(null)
    if (result.ok) await reload()
    else setError(describeError(result.error))
  }

  const remove = async (memberId: string): Promise<void> => {
    if (!project) return
    setBusyId(memberId)
    setError(null)
    const result = await window.jyteams.tickets.unshare(project.id, memberId)
    setBusyId(null)
    if (result.ok) await reload()
    else setError(describeError(result.error))
  }

  const isOwner =
    project !== null &&
    current.some((member) => member.id === currentMemberId && member.role === 'owner')
  const present = new Set(current.map((member) => member.id))
  const candidates = members.filter((member) => !present.has(member.id))

  return (
    <Dialog
      open={open}
      title={`Share ${project?.name ?? 'this project'}`}
      subtitle="Everyone here can read and edit the project. Tickets stay personal."
      onClose={onClose}
      footer={
        <>
          <span className="spacer" />
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Done
          </button>
        </>
      }
    >
      {!isOwner ? (
        <div className="notice notice--warn">
          Only the project&apos;s owner can change who has access. You can see the list below.
        </div>
      ) : null}

      {error ? <div className="notice notice--error">{error}</div> : null}

      <span className="side__label">People with access</span>
      <ul className="share-list">
        {current.map((member) => (
          <li key={member.id} className="share-row">
            <span className="share-row__name">{member.display_name}</span>
            <span className="badge">{member.role}</span>
            {isOwner && member.role !== 'owner' ? (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                disabled={busyId === member.id}
                onClick={() => void remove(member.id)}
              >
                {busyId === member.id ? <Spinner label="Removing" /> : 'Remove'}
              </button>
            ) : null}
          </li>
        ))}
      </ul>

      {isOwner ? (
        <>
          <span className="side__label">Add someone</span>
          {candidates.length === 0 ? (
            <p className="side__empty">
              Everyone who has signed in is already on this project. A new name appears here after
              that person picks it on the startup screen.
            </p>
          ) : (
            <ul className="share-list">
              {candidates.map((member) => (
                <li key={member.id} className="share-row">
                  <span className="share-row__name">{member.display_name}</span>
                  <button
                    type="button"
                    className="btn btn--sm"
                    disabled={busyId === member.id}
                    onClick={() => void add(member.id)}
                  >
                    {busyId === member.id ? <Spinner label="Sharing" /> : 'Add'}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </Dialog>
  )
}

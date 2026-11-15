/**
 * The startup name picker. There is no password: choosing a name is signing in, and the chosen
 * member id is what the backend treats as the caller.
 */

import { useState } from 'react'

import type { ApiError, Member } from '@shared/types'

import { describeError } from '../lib/errors'
import { initials } from '../lib/tickets'
import { ErrorBox, Spinner } from './primitives'

export function IdentityGate({
  members,
  loading,
  error,
  onPick,
  onRetry,
  onOpenSettings
}: {
  members: Member[]
  loading: boolean
  error: ApiError | null
  onPick: (displayName: string) => Promise<boolean>
  onRetry: () => void
  onOpenSettings: () => void
}) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)

  const pick = async (value: string): Promise<void> => {
    const trimmed = value.trim()
    if (!trimmed) return
    setBusy(true)
    setFailure(null)
    const ok = await onPick(trimmed)
    if (!ok) setFailure('That name could not be used. Check the backend and try again.')
    setBusy(false)
  }

  return (
    <div className="gate">
      <div className="gate__panel">
        <div className="gate__mark" aria-hidden="true">
          JY
        </div>
        <h1 className="gate__title">Who are you?</h1>
        <p className="gate__lede">
          Pick your name to see your tickets. Different names are different people — no password,
          because this is a hackathon build.
        </p>

        {loading ? (
          <p className="gate__status">
            <Spinner label="Loading names" /> Reading the member list.
          </p>
        ) : null}

        {!loading && error ? (
          <ErrorBox title="The backend could not be reached" detail={describeError(error)}>
            <button type="button" className="btn btn--sm" onClick={onRetry}>
              Try again
            </button>
            <button type="button" className="btn btn--ghost btn--sm" onClick={onOpenSettings}>
              Settings
            </button>
          </ErrorBox>
        ) : null}

        {!loading && !error && members.length > 0 ? (
          <>
            <span className="gate__label">Already a member</span>
            <div className="gate__names">
              {members.map((member) => (
                <button
                  key={member.id}
                  type="button"
                  className="gate__name"
                  onClick={() => void pick(member.display_name)}
                  disabled={busy}
                >
                  <span className="avatar">{initials(member.display_name)}</span>
                  <span>{member.display_name}</span>
                </button>
              ))}
            </div>
          </>
        ) : null}

        {!loading && !error ? (
          <form
            className="gate__form"
            onSubmit={(event) => {
              event.preventDefault()
              void pick(name)
            }}
          >
            <label className="field">
              <span className="field__label">I&apos;m new — my name</span>
              <input
                className="field__input"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Charlie Park"
                maxLength={60}
                autoFocus={members.length === 0}
              />
            </label>
            <button type="submit" className="btn btn--primary" disabled={busy || !name.trim()}>
              {busy ? <Spinner label="Signing in" /> : null}
              Continue
            </button>
          </form>
        ) : null}

        {failure ? <p className="gate__error">{failure}</p> : null}

        <p className="gate__foot">
          The name is remembered on this computer. Use the identity chip in the rail to switch.
        </p>
      </div>
    </div>
  )
}

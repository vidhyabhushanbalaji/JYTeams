/** The list that opens when somebody types `@` in the composer. */

import type { ApiError, MentionTarget } from '@shared/types'

import { mentionIcon } from '../lib/chat'
import { describeError } from '../lib/errors'
import { Spinner } from './primitives'

export function MentionPicker({
  targets,
  loading,
  active,
  error,
  onHover,
  onPick
}: {
  targets: MentionTarget[]
  loading: boolean
  active: number
  error: ApiError | null
  onHover: (index: number) => void
  onPick: (target: MentionTarget) => void
}) {
  return (
    <div className="mention-picker" role="listbox" aria-label="Mention something in this project">
      <span className="mention-picker__title">
        Mention a document, a folder or a ticket
        {loading ? <Spinner label="Searching" /> : null}
      </span>

      {error ? <p className="mention-picker__empty">{describeError(error)}</p> : null}

      {!error && targets.length === 0 && !loading ? (
        <p className="mention-picker__empty">Nothing in this project matches that.</p>
      ) : null}

      <ul className="mention-picker__list">
        {targets.map((target, index) => (
          <li key={`${target.kind}:${target.id}`}>
            <button
              type="button"
              role="option"
              aria-selected={index === active}
              className={`mention-option${index === active ? ' mention-option--active' : ''}`}
              onMouseEnter={() => onHover(index)}
              onClick={() => onPick(target)}
            >
              <span className="mention-option__icon" aria-hidden="true">
                {mentionIcon(target.kind)}
              </span>
              <span className="mention-option__body">
                <span className="mention-option__label">{target.label}</span>
                <span className="mention-option__detail">
                  {target.kind === 'ticket' ? target.detail : target.path || target.detail}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

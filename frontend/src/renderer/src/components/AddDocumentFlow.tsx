/**
 * The two-step add wizard, driven by the real contract: POST /suggestions, then
 * POST /placements. A 409 comes back with the names that are free, so a clash is resolved
 * here instead of being re-uploaded; a 410 means the suggestion expired and the file has to
 * be offered again.
 */

import { useCallback, useEffect, useState } from 'react'

import type {
  AddSuggestion,
  ApiError,
  PickedFile,
  PlacementMode,
  PlacementResult,
  SuggestionAccepted
} from '@shared/types'

import { describeError, isExpired, retryNames } from '../lib/errors'
import { humanBytes, scoreText } from '../lib/format'
import { documentPreview, scanSummary, visibleTerms } from '../lib/payloads'
import { Dialog, Spinner } from './primitives'

type Step = 'choose' | 'suggesting' | 'suggested' | 'placing' | 'error'

function conflictTarget(error: ApiError): 'file' | 'folder' {
  const detail = error.detail
  if (!detail || typeof detail !== 'object') return 'file'
  const conflict = (detail as Record<string, unknown>).conflict
  if (!conflict || typeof conflict !== 'object') return 'file'
  return 'existing_file_id' in (conflict as Record<string, unknown>) ? 'file' : 'folder'
}

export function AddDocumentFlow({
  open,
  projectId,
  context,
  onClose,
  onPlaced
}: {
  open: boolean
  projectId: string
  /** A ticket's title and description, which may steer the ranking (optional). */
  context?: string
  onClose: () => void
  onPlaced: (result: PlacementResult) => void
}) {
  const [step, setStep] = useState<Step>('choose')
  const [file, setFile] = useState<PickedFile | null>(null)
  const [suggestion, setSuggestion] = useState<SuggestionAccepted | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)
  const [placement, setPlacement] = useState<PlacementMode>('direct')
  const [newFolderName, setNewFolderName] = useState('')
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState<ApiError | null>(null)
  const [names, setNames] = useState<string[]>([])
  const [target, setTarget] = useState<'file' | 'folder'>('file')

  const reset = useCallback(() => {
    setStep('choose')
    setFile(null)
    setSuggestion(null)
    setChosen(null)
    setPlacement('direct')
    setNewFolderName('')
    setFileName('')
    setError(null)
    setNames([])
  }, [])

  useEffect(() => {
    if (!open) reset()
  }, [open, reset])

  const selected: AddSuggestion | null =
    suggestion?.suggestions.find((item) => item.directory_id === chosen) ?? null

  const pick = async (): Promise<void> => {
    const picked = await window.jyteams.add.pickFile()
    if (!picked) return
    setFile(picked)
    setError(null)
    setStep('suggesting')
    const result = await window.jyteams.add.suggest({
      projectId,
      filePath: picked.path,
      context
    })
    if (!result.ok) {
      setError(result.error)
      setStep('error')
      return
    }
    setSuggestion(result.data)
    const first = result.data.suggestions[0]
    if (first) {
      setChosen(first.directory_id)
      setNewFolderName(first.proposed_new_directory_names[0] ?? '')
    }
    setStep('suggested')
  }

  const choose = (item: AddSuggestion): void => {
    setChosen(item.directory_id)
    setPlacement('direct')
    setNewFolderName(item.proposed_new_directory_names[0] ?? '')
    setFileName('')
    setError(null)
    setNames([])
  }

  const place = async (): Promise<void> => {
    if (!suggestion || !chosen) return
    setError(null)
    setStep('placing')
    const result = await window.jyteams.add.place({
      request_id: suggestion.request_id,
      directory_id: chosen,
      placement,
      new_directory_name: placement === 'new_directory' ? newFolderName.trim() : null,
      file_name: fileName.trim() ? fileName.trim() : null
    })
    if (result.ok) {
      onPlaced(result.data)
      onClose()
      return
    }
    setError(result.error)
    setNames(retryNames(result.error, selected))
    setTarget(conflictTarget(result.error))
    setStep('suggested')
  }

  const canPlace =
    Boolean(selected) &&
    !(placement === 'new_directory' && newFolderName.trim().length === 0) &&
    step !== 'placing'

  return (
    <Dialog
      open={open}
      title="Add a document"
      subtitle="Find the folder it belongs in, then put it there."
      onClose={onClose}
      footer={
        step === 'choose' || step === 'error' ? (
          <>
            <span className="spacer" />
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn btn--primary" onClick={() => void pick()}>
              {step === 'error' ? 'Choose another file' : 'Choose file'}
            </button>
          </>
        ) : step === 'suggesting' ? (
          <>
            <span className="spacer" />
            <span className="field__hint">Looking for the right folder…</span>
          </>
        ) : step === 'placing' ? (
          <>
            <span className="spacer" />
            <span className="field__hint">Writing the file…</span>
          </>
        ) : (
          <>
            <button type="button" className="btn btn--ghost" onClick={reset}>
              Choose another file
            </button>
            <span className="spacer" />
            <button type="button" className="btn btn--primary" onClick={() => void place()} disabled={!canPlace}>
              Place document
            </button>
          </>
        )
      }
    >
      {file ? (
        <div className="doc-summary">
          <span className="doc-summary__name">
            {file.name}
            <span className="muted">{humanBytes(file.sizeBytes)}</span>
          </span>
          {suggestion ? <p className="doc-summary__text">{documentPreview(suggestion.file)}</p> : null}
        </div>
      ) : null}

      {step === 'choose' ? (
        <p className="side__empty">
          Every folder is scored locally against the document&apos;s title, filename and most
          frequent terms — no model is called. The best three are offered and the project root is
          always available as a fallback.
        </p>
      ) : null}

      {step === 'suggesting' ? (
        <div className="side__section">
          <span className="side__label">Reading the tree</span>
          <p className="side__text">
            <Spinner label="Finding a place" />{' '}
            <span style={{ marginLeft: 8 }}>Scoring every folder against the document.</span>
          </p>
        </div>
      ) : null}

      {step === 'error' && error ? (
        <>
          <div className="notice notice--error">{describeError(error)}</div>
          {isExpired(error) ? (
            <p className="side__empty">A suggestion is only good for 24 hours. Choose the file again to get a fresh one.</p>
          ) : null}
        </>
      ) : null}

      {step === 'suggested' && suggestion ? (
        <>
          <div className="suggestions">
            {suggestion.suggestions.map((item) => (
              <button
                key={item.directory_id}
                type="button"
                className={`suggestion${chosen === item.directory_id ? ' suggestion--active' : ''}`}
                onClick={() => choose(item)}
                aria-pressed={chosen === item.directory_id}
              >
                <span className="suggestion__top">
                  <span className="suggestion__name">{item.path ? item.name : 'Project root'}</span>
                  <span className="suggestion__path">{item.path || '(root)'}</span>
                  <span className="suggestion__score">{scoreText(item.score)}</span>
                </span>
                <span className="suggestion__bar">
                  <span
                    className="suggestion__fill"
                    style={{ display: 'block', width: `${Math.round(item.score * 100)}%` }}
                  />
                </span>
                <span className="suggestion__reason">{item.reason}</span>
                {item.matched_terms.length > 0 ? (
                  <span className="chips">
                    {visibleTerms(item.matched_terms).map((term) => (
                      <span key={term} className="chip">
                        {term}
                      </span>
                    ))}
                  </span>
                ) : null}
                <span className="suggestion__meta">
                  {item.direct_file_count} files · {item.child_directory_count} folders
                  {item.is_leaf ? ' · leaf' : ''}
                  {item.identical_content_at.length > 0 ? ' · same content already here' : ''}
                </span>
              </button>
            ))}
          </div>

          <p className="side__empty">{scanSummary(suggestion.scan)}</p>

          {selected ? (
            <div className="choice">
              <span className="side__label">Where in {selected.path || 'the project root'}</span>
              <div className="choice__row">
                <button
                  type="button"
                  className={`btn btn--sm${placement === 'direct' ? ' btn--primary' : ''}`}
                  onClick={() => setPlacement('direct')}
                  aria-pressed={placement === 'direct'}
                >
                  Put it in this folder
                </button>
                <button
                  type="button"
                  className={`btn btn--sm${placement === 'new_directory' ? ' btn--primary' : ''}`}
                  onClick={() => setPlacement('new_directory')}
                  aria-pressed={placement === 'new_directory'}
                >
                  Create a folder here
                </button>
              </div>

              {placement === 'new_directory' ? (
                <>
                  <label className="field">
                    <span className="field__label">New folder name</span>
                    <input
                      className="field__input"
                      value={newFolderName}
                      onChange={(event) => setNewFolderName(event.target.value)}
                      placeholder="authentication"
                    />
                  </label>
                  {selected.proposed_new_directory_names.length > 0 ? (
                    <div className="chips">
                      {selected.proposed_new_directory_names.map((name) => (
                        <button key={name} type="button" className="chip" onClick={() => setNewFolderName(name)}>
                          {name}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </>
              ) : null}

              {selected.suggested_file_names.length > 0 ? (
                <>
                  <span className="field__label">A file with this name is already there. Rename it to:</span>
                  <div className="chips">
                    {selected.suggested_file_names.map((name) => (
                      <button
                        key={name}
                        type="button"
                        className={`chip${fileName === name ? ' badge--ink' : ''}`}
                        onClick={() => setFileName(name)}
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                </>
              ) : null}

              {selected.identical_content_at.length > 0 ? (
                <div className="notice notice--warn">
                  The same bytes are already stored at {selected.identical_content_at.join(', ')}. Placing
                  this again makes a second copy on purpose.
                </div>
              ) : null}

              {error ? (
                <div className="notice notice--error">
                  {describeError(error)}
                  {names.length > 0 ? (
                    <div className="chips">
                      {names.map((name) => (
                        <button
                          key={name}
                          type="button"
                          className="chip"
                          onClick={() => (target === 'file' ? setFileName(name) : setNewFolderName(name))}
                        >
                          Use {name}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
        </>
      ) : null}
    </Dialog>
  )
}
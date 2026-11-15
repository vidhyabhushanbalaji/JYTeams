/**
 * The add wizard, driven by the real contract: POST /suggestions, then POST /placements.
 *
 * A document either comes from disk (the file picker) or is written here in the markdown
 * editor. Both paths post the same multipart shape - a written document is encoded to bytes in
 * the main process - so ranking, placement and the one description call are identical. A 409
 * comes back with the names that are free, so a clash is resolved here instead of being
 * re-uploaded; a 410 means the suggestion expired and the document has to be offered again.
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

import { DRAFT_PLACEHOLDER, draftFileName, draftSizeBytes } from '../lib/documentDraft'
import { describeError, isExpired, retryNames } from '../lib/errors'
import { humanBytes, scoreText } from '../lib/format'
import { wordCount } from '../lib/markdown'
import { documentPreview, scanSummary, visibleTerms } from '../lib/payloads'
import { EditorTabs, MarkdownEditor, type MarkdownMode } from './MarkdownEditor'
import { Dialog, Spinner } from './primitives'

type Step = 'choose' | 'compose' | 'suggesting' | 'suggested' | 'placing' | 'error'

/** Where the placed document came from: the caller may open it only when it was just written. */
export type PlacementOrigin = 'upload' | 'draft'

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
  onPlaced: (result: PlacementResult, origin: PlacementOrigin) => void
}) {
  const [step, setStep] = useState<Step>('choose')
  const [file, setFile] = useState<PickedFile | null>(null)
  const [draftName, setDraftName] = useState('')
  const [draftText, setDraftText] = useState('')
  const [editorMode, setEditorMode] = useState<MarkdownMode>('edit')
  //: True while the document being placed was written here rather than picked from disk.
  const [drafting, setDrafting] = useState(false)
  const [discarding, setDiscarding] = useState(false)
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
    setDraftName('')
    setDraftText('')
    setEditorMode('edit')
    setDrafting(false)
    setDiscarding(false)
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

  const draft = draftFileName(draftName)
  const draftReady = draft.error === null && draftText.trim().length > 0

  const selected: AddSuggestion | null =
    suggestion?.suggestions.find((item) => item.directory_id === chosen) ?? null

  const accept = useCallback((data: SuggestionAccepted): void => {
    setSuggestion(data)
    const first = data.suggestions[0]
    if (first) {
      setChosen(first.directory_id)
      setNewFolderName(first.proposed_new_directory_names[0] ?? '')
    }
    setStep('suggested')
  }, [])

  const startCompose = (): void => {
    setDrafting(true)
    setFile(null)
    setSuggestion(null)
    setEditorMode('edit')
    setError(null)
    setNames([])
    setStep('compose')
  }

  const backToCompose = (): void => {
    setError(null)
    setNames([])
    setStep('compose')
  }

  /** Closing while a body has been written asks first; nothing typed is thrown away silently. */
  const closeWithConfirm = useCallback((): void => {
    if (draftText.trim().length > 0) {
      setDiscarding(true)
      return
    }
    onClose()
  }, [draftText, onClose])

  const pick = async (): Promise<void> => {
    const picked = await window.jyteams.add.pickFile()
    if (!picked) return
    setFile(picked)
    setDrafting(false)
    setSuggestion(null)
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
    accept(result.data)
  }

  const findDraftFolder = async (): Promise<void> => {
    if (!draftReady) return
    setDrafting(true)
    setSuggestion(null)
    setError(null)
    setNames([])
    setStep('suggesting')
    const result = await window.jyteams.add.suggestDraft({
      projectId,
      fileName: draft.name,
      text: draftText,
      context
    })
    if (!result.ok) {
      setError(result.error)
      setStep('compose')
      return
    }
    accept(result.data)
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
      onPlaced(result.data, drafting ? 'draft' : 'upload')
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
      wide={step === 'compose'}
      title={step === 'compose' ? 'New document' : 'Add a document'}
      subtitle={
        step === 'compose'
          ? 'Write it here, then choose the folder it belongs in.'
          : 'Find the folder it belongs in, then put it there.'
      }
      onClose={step === 'compose' ? closeWithConfirm : onClose}
      footer={
        step === 'choose' || step === 'error' ? (
          <>
            <span className="spacer" />
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn" onClick={startCompose}>
              Write a document
            </button>
            <button type="button" className="btn btn--primary" onClick={() => void pick()}>
              {step === 'error' ? 'Choose another file' : 'Choose file'}
            </button>
          </>
        ) : step === 'compose' ? (
          discarding ? (
            <>
              <span className="sheet__note">Discard this document?</span>
              <span className="spacer" />
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setDiscarding(false)}
              >
                Keep writing
              </button>
              <button type="button" className="btn btn--sm" onClick={onClose}>
                Discard
              </button>
            </>
          ) : (
            <>
              <span className="field__hint">
                {draftReady ? 'Ready to find a folder.' : 'A name and some text are required.'}
              </span>
              <span className="spacer" />
              <button type="button" className="btn btn--ghost" onClick={closeWithConfirm}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => void findDraftFolder()}
                disabled={!draftReady}
              >
                Find a folder
              </button>
            </>
          )
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
            <button
              type="button"
              className="btn btn--ghost"
              onClick={drafting ? backToCompose : reset}
            >
              {drafting ? 'Back to the editor' : 'Choose another file'}
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

      {drafting && step !== 'compose' ? (
        <div className="doc-summary">
          <span className="doc-summary__name">
            {draft.name || 'New document'}
            <span className="muted">{humanBytes(draftSizeBytes(draftText))}</span>
          </span>
          {suggestion ? <p className="doc-summary__text">{documentPreview(suggestion.file)}</p> : null}
        </div>
      ) : null}

      {step === 'choose' ? (
        <p className="side__empty">
          Upload a markdown file, or write a new one here — it joins the tree the same way. Every
          folder is scored locally against the document&apos;s title, filename and most frequent
          terms, so no model is called: the best three are offered and the project root is always
          available as a fallback.
        </p>
      ) : null}

      {step === 'compose' ? (
        <div className="compose">
          {error ? <div className="notice notice--error">{describeError(error)}</div> : null}

          <label className="field">
            <span className="field__label">File name</span>
            <input
              className="field__input"
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && draftReady) {
                  event.preventDefault()
                  void findDraftFolder()
                }
              }}
              placeholder="release-checklist.md"
              aria-invalid={draft.error ? true : undefined}
              autoFocus
            />
            <span className={draft.error ? 'field__hint field__hint--error' : 'field__hint'}>
              {draft.error ??
                (draft.name ? `Stored as ${draft.name}` : 'Markdown only — .md is added for you.')}
            </span>
          </label>

          <div className="compose__editor">
            <div className="compose__bar">
              <span className="field__label">Document</span>
              <span className="spacer" />
              <span className="field__hint">
                {wordCount(draftText)} words · {draftText.length.toLocaleString()} characters
              </span>
              <EditorTabs mode={editorMode} onChange={setEditorMode} label="Document mode" />
            </div>
            <MarkdownEditor
              mode={editorMode}
              value={draftText}
              onChange={setDraftText}
              label={`Writing ${draft.name || 'a new document'}`}
              placeholder={DRAFT_PLACEHOLDER}
            />
          </div>

          <p className="side__empty">
            The document joins the graph only when you place it, and the folder it lands in is
            described from its text.
          </p>
        </div>
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
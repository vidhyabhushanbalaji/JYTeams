/**
 * The document sheet: one markdown file, read or edited over the canvas.
 *
 * A double-click on a file card (or the Inspector's button) opens it. Reading renders the
 * markdown; editing swaps in a plain textarea, because a document stored as text is edited
 * faithfully as text. Saving sends the digest it was read from, so two windows cannot silently
 * overwrite each other.
 */

import { useCallback, useEffect, useState } from 'react'

import type { FileSaved } from '@shared/types'

import { describeError } from '../lib/errors'
import { humanBytes } from '../lib/format'
import { wordCount } from '../lib/markdown'
import { useDocument } from '../state/useDocument'
import { EditorTabs, MarkdownEditor } from './MarkdownEditor'
import { ErrorBox, Spinner } from './primitives'

export function DocumentSheet({
  fileId,
  onClose,
  onSaved
}: {
  fileId: string | null
  onClose: () => void
  onSaved: (saved: FileSaved) => void
}) {
  const doc = useDocument()
  const { open, close, showRead, beginEdit, discard, save, setDraft } = doc
  const { file, status, error, saveError, draft, mode, saving, savedAt, dirty } = doc
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!fileId) {
      close()
      return
    }
    setConfirming(false)
    void open(fileId)
  }, [fileId, open, close])

  const finishClose = useCallback((): void => {
    close()
    onClose()
  }, [close, onClose])

  const requestClose = useCallback((): void => {
    if (dirty && mode === 'edit') {
      setConfirming(true)
      return
    }
    finishClose()
  }, [dirty, mode, finishClose])

  const saveNow = useCallback(async (): Promise<void> => {
    if (!dirty || saving) return
    const saved = await save()
    if (saved) onSaved(saved)
  }, [save, dirty, saving, onSaved])

  useEffect(() => {
    if (!fileId) return undefined
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault()
        requestClose()
      } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        void saveNow()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [fileId, requestClose, saveNow])

  if (!fileId) return null

  const editing = mode === 'edit' && file?.editable === true

  return (
    <div className="sheet">
      <div className="sheet__scrim" role="presentation" onMouseDown={requestClose} />
      <section
        className="sheet__panel"
        role="dialog"
        aria-modal="true"
        aria-label={file?.name ?? 'Document'}
      >
        <header className="sheet__head">
          <div className="sheet__titles">
            <h2 className="sheet__title">{file?.name ?? 'Opening\u2026'}</h2>
            {file ? <p className="sheet__path">{file.path}</p> : null}
          </div>
          <span className="spacer" />
          {file?.editable ? (
            <EditorTabs
              mode={editing ? 'edit' : 'read'}
              onChange={(next) => (next === 'edit' ? beginEdit() : showRead())}
            />
          ) : null}
          {dirty ? (
            <span className="sheet__dirty" title="Unsaved changes" aria-hidden="true" />
          ) : null}
          <button
            type="button"
            className="btn btn--ghost btn--icon"
            onClick={requestClose}
            aria-label="Close"
          >
            {'\u00d7'}
          </button>
        </header>

        <div className={editing ? 'sheet__body sheet__body--edit' : 'sheet__body'}>
          {status === 'loading' ? (
            <div className="canvas__state">
              <Spinner label="Opening the document" />
              <p className="canvas__state-text">Reading the stored markdown.</p>
            </div>
          ) : null}

          {status === 'error' && error ? (
            <ErrorBox title="This document could not be opened" detail={describeError(error)}>
              <button type="button" className="btn" onClick={() => void open(fileId)}>
                Try again
              </button>
            </ErrorBox>
          ) : null}

          {status === 'ready' && file ? (
            <MarkdownEditor
              mode={editing ? 'edit' : 'read'}
              value={editing ? draft : file.text}
              onChange={setDraft}
              label={`Editing ${file.name}`}
              autoFocus
            />
          ) : null}
        </div>

        <footer className="sheet__foot">
          {file ? (
            <span>
              {editing
                ? `${wordCount(draft)} words \u00b7 ${draft.length.toLocaleString()} characters`
                : `${wordCount(file.text)} words \u00b7 ${humanBytes(file.size_bytes)}`}
            </span>
          ) : null}

          {file?.truncated ? (
            <span className="sheet__note">
              Only the first {file.text.length.toLocaleString()} characters are shown, so this
              document opens read-only.
            </span>
          ) : null}

          {saveError ? (
            <span className="sheet__note sheet__note--error">{describeError(saveError)}</span>
          ) : null}

          {savedAt && !dirty ? <span className="sheet__note">Saved</span> : null}

          <span className="spacer" />

          {confirming ? (
            <>
              <span className="sheet__note">Discard your changes?</span>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setConfirming(false)}
              >
                Keep editing
              </button>
              <button type="button" className="btn btn--sm" onClick={finishClose}>
                Discard
              </button>
            </>
          ) : editing ? (
            <>
              <button
                type="button"
                className="btn btn--ghost"
                onClick={discard}
                disabled={!dirty || saving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => void saveNow()}
                disabled={!dirty || saving}
              >
                {saving ? <Spinner label="Saving" /> : null}
                Save
              </button>
            </>
          ) : (
            <button type="button" className="btn" onClick={requestClose}>
              Close
            </button>
          )}
        </footer>
      </section>
    </div>
  )
}

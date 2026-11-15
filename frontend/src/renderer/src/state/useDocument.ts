/**
 * The document sheet's state: load one body, edit a draft, save it against the digest it was
 * read from. Saving is a storage write plus a row update - no model is called, so folder
 * descriptions refresh on the next add or placement rather than here.
 */

import { useCallback, useRef, useState } from 'react'

import type { ApiError, FileContent, FileSaved } from '@shared/types'

export type DocumentStatus = 'idle' | 'loading' | 'ready' | 'error'
export type DocumentMode = 'read' | 'edit'

export function useDocument() {
  const [status, setStatus] = useState<DocumentStatus>('idle')
  const [error, setError] = useState<ApiError | null>(null)
  const [saveError, setSaveError] = useState<ApiError | null>(null)
  const [file, setFile] = useState<FileContent | null>(null)
  const [draft, setDraft] = useState('')
  const [mode, setMode] = useState<DocumentMode>('read')
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<number | null>(null)

  // Opening another document while one is still loading must not let the older reply win.
  const latest = useRef(0)

  const open = useCallback(async (fileId: string): Promise<void> => {
    const nonce = latest.current + 1
    latest.current = nonce
    setStatus('loading')
    setError(null)
    setSaveError(null)
    setFile(null)
    setDraft('')
    setMode('read')
    setSavedAt(null)

    const result = await window.jyteams.files.read(fileId)
    if (nonce !== latest.current) return
    if (!result.ok) {
      setStatus('error')
      setError(result.error)
      return
    }
    setFile(result.data)
    setDraft(result.data.text)
    setStatus('ready')
  }, [])

  const close = useCallback((): void => {
    latest.current += 1
    setStatus('idle')
    setError(null)
    setSaveError(null)
    setFile(null)
    setDraft('')
    setMode('read')
    setSavedAt(null)
  }, [])

  const beginEdit = useCallback((): void => setMode('edit'), [])
  const showRead = useCallback((): void => setMode('read'), [])

  const discard = useCallback((): void => {
    setDraft(file?.text ?? '')
    setSaveError(null)
    setMode('read')
  }, [file])

  const save = useCallback(async (): Promise<FileSaved | null> => {
    if (!file || !file.editable || saving) return null
    setSaving(true)
    setSaveError(null)

    const result = await window.jyteams.files.save({
      fileId: file.id,
      text: draft,
      expectedSha256: file.content_sha256
    })
    setSaving(false)

    if (!result.ok) {
      setSaveError(result.error)
      return null
    }

    setFile((current) =>
      current
        ? {
            ...current,
            text: draft,
            content_sha256: result.data.content_sha256,
            size_bytes: result.data.size_bytes
          }
        : current
    )
    setSavedAt(Date.now())
    return result.data
  }, [draft, file, saving])

  return {
    status,
    error,
    saveError,
    file,
    draft,
    mode,
    saving,
    savedAt,
    dirty: file !== null && draft !== file.text,
    open,
    close,
    beginEdit,
    showRead,
    discard,
    save,
    setDraft
  }
}

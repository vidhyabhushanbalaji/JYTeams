/**
 * Choose a folder, see exactly what will be sent, then follow the background job.
 *
 * The upload itself only ingests the files (the API answers 202 with a job id); every
 * summary is produced afterwards, so the progress bar is driven by GET /jobs/{id} until it
 * reports ok, partial or failed.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import type { CreationJob, FolderPreview } from '@shared/types'

import { describeError } from '../lib/errors'
import { humanBytes, plural } from '../lib/format'
import { Dialog, Field, Spinner } from './primitives'

type Step = 'choose' | 'review' | 'uploading' | 'running' | 'error'

const STEP_LABEL: Record<string, string> = {
  queued: 'Queued',
  summarising: 'Summarising',
  persisting: 'Writing the tree',
  ok: 'Done',
  partial: 'Done, with skipped files',
  failed: 'Failed'
}

export function NewProjectFlow({
  open,
  onClose,
  onCreated
}: {
  open: boolean
  onClose: () => void
  onCreated: (projectId: string) => void
}) {
  const [step, setStep] = useState<Step>('choose')
  const [folderPath, setFolderPath] = useState<string | null>(null)
  const [preview, setPreview] = useState<FolderPreview | null>(null)
  const [name, setName] = useState('')
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<CreationJob | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const created = useRef(onCreated)
  created.current = onCreated

  const reset = useCallback(() => {
    setStep('choose')
    setFolderPath(null)
    setPreview(null)
    setName('')
    setJobId(null)
    setJob(null)
    setError(null)
    setBusy(false)
  }, [])

  useEffect(() => {
    if (!open) reset()
  }, [open, reset])

  useEffect(() => {
    if (step !== 'running' || !jobId) return

    let cancelled = false
    let failures = 0
    let timer: ReturnType<typeof setTimeout>

    const tick = async (): Promise<void> => {
      const result = await window.jyteams.projects.job(jobId)
      if (cancelled) return

      if (!result.ok) {
        failures += 1
        if (failures >= 3) {
          setError(describeError(result.error))
          setStep('error')
          return
        }
      } else {
        failures = 0
        setJob(result.data)
        if (result.data.status === 'ok' || result.data.status === 'partial') {
          created.current(result.data.project_id)
          return
        }
        if (result.data.status === 'failed') {
          setError(result.data.error ?? 'The upload failed before the tree was written.')
          setStep('error')
          return
        }
      }

      timer = setTimeout(() => void tick(), 1500)
    }

    timer = setTimeout(() => void tick(), 600)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [step, jobId])

  const pick = async (): Promise<void> => {
    const path = await window.jyteams.create.pickFolder()
    if (!path) return
    setBusy(true)
    const result = await window.jyteams.create.preview(path)
    setBusy(false)
    if (!result.ok) {
      setError(describeError(result.error))
      setStep('error')
      return
    }
    setFolderPath(path)
    setPreview(result.data)
    setName(result.data.name)
    setStep('review')
  }

  const create = async (): Promise<void> => {
    if (!folderPath || !name.trim()) return
    setError(null)
    setStep('uploading')
    const result = await window.jyteams.create.upload({ name: name.trim(), folderPath })
    if (!result.ok) {
      setError(describeError(result.error))
      setStep('error')
      return
    }
    setJobId(result.data.job_id)
    setStep('running')
  }

  const progress = job && job.total_files > 0 ? Math.round((job.processed_files / job.total_files) * 100) : 0

  return (
    <Dialog
      open={open}
      title="New project"
      subtitle="A folder of markdown files becomes a described tree."
      onClose={onClose}
      footer={
        step === 'choose' ? (
          <>
            <span className="spacer" />
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn btn--primary" onClick={() => void pick()} disabled={busy}>
              {busy ? <Spinner label="Reading the folder" /> : null}
              Choose folder
            </button>
          </>
        ) : step === 'review' ? (
          <>
            <button type="button" className="btn btn--ghost" onClick={reset}>
              Choose another
            </button>
            <span className="spacer" />
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => void create()}
              disabled={!name.trim() || (preview?.fileCount ?? 0) === 0}
            >
              Create project
            </button>
          </>
        ) : step === 'error' ? (
          <>
            <span className="spacer" />
            <button type="button" className="btn" onClick={reset}>
              Start again
            </button>
            <button type="button" className="btn btn--ghost" onClick={onClose}>
              Close
            </button>
          </>
        ) : (
          <>
            <span className="spacer" />
            <span className="field__hint">You can leave this open; the job keeps running.</span>
          </>
        )
      }
    >
      {step === 'choose' ? (
        <>
          <p className="side__text">
            Pick the folder that holds your documentation. Only <span className="mono">.md</span>,{' '}
            <span className="mono">.markdown</span> and <span className="mono">.mdx</span> files are
            read; everything else is listed as skipped.
          </p>
          <p className="side__empty">
            Folders named node_modules, .git, dist, build and other generated directories are not
            walked. Hidden files are ignored.
          </p>
        </>
      ) : null}

      {step === 'review' && preview ? (
        <>
          <Field label="Project name">
            <input
              className="field__input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoFocus
            />
          </Field>
          <div className="preview">
            <div className="preview__row">
              <span className="preview__key">Folder</span>
              <span className="preview__value" style={{ overflowWrap: 'anywhere' }}>
                {preview.path}
              </span>
            </div>
            <div className="preview__row">
              <span className="preview__key">Markdown</span>
              <span className="preview__value">{plural(preview.fileCount, 'file')}</span>
            </div>
            <div className="preview__row">
              <span className="preview__key">Size</span>
              <span className="preview__value">{humanBytes(preview.totalBytes)}</span>
            </div>
            {preview.skippedCount > 0 ? (
              <div className="preview__row">
                <span className="preview__key">Skipped</span>
                <span className="preview__value">{plural(preview.skippedCount, 'other file')}</span>
              </div>
            ) : null}
          </div>
          {preview.problems.map((problem) => (
            <div key={problem} className="notice notice--warn">
              {problem}
            </div>
          ))}
          {preview.fileCount === 0 ? (
            <div className="notice notice--error">
              That folder has no markdown files, so there would be nothing to describe.
            </div>
          ) : null}
        </>
      ) : null}

      {step === 'uploading' ? (
        <div className="side__section">
          <span className="side__label">Uploading</span>
          <p className="side__text">
            <Spinner label="Uploading" /> <span style={{ marginLeft: 8 }}>Sending the files to the backend.</span>
          </p>
        </div>
      ) : null}

      {step === 'running' && job ? (
        <div className="progress">
          <div className="progress__label">
            <span className="progress__step">{STEP_LABEL[job.status] ?? job.status}</span>
            <span className="progress__meta">
              {job.processed_files}/{job.total_files} files
            </span>
          </div>
          <div className="progress__track">
            <div className="progress__fill" style={{ width: `${progress}%` }} />
          </div>
          <p className="side__empty">
            Every file is summarised, then every folder is described from the summaries below it,
            finishing with the root. Nothing is written until all of that has succeeded.
          </p>
        </div>
      ) : null}

      {step === 'error' && error ? <div className="notice notice--error">{error}</div> : null}
    </Dialog>
  )
}
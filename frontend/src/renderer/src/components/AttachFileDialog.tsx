/**
 * Attach a document that is already in the project.
 *
 * The picker is a Graph AI Search over the project, which costs no model call — so a ticket can
 * borrow the same relevance the graph uses.
 */

import { useEffect, useState } from 'react'

import type { SearchHit } from '@shared/types'

import { describeError } from '../lib/errors'
import { scoreText } from '../lib/format'
import { Dialog, Spinner } from './primitives'

export function AttachFileDialog({
  open,
  projectId,
  attachedIds,
  onClose,
  onAttach
}: {
  open: boolean
  projectId: string
  attachedIds: ReadonlySet<string>
  onClose: () => void
  onAttach: (fileId: string) => Promise<void>
}) {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [running, setRunning] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setQuery('')
    setHits([])
    setError(null)
  }, [open])

  const run = async (): Promise<void> => {
    const trimmed = query.trim()
    if (trimmed.length < 3) {
      setError('Type at least three characters to search the project.')
      return
    }
    setRunning(true)
    setError(null)
    const result = await window.jyteams.search.run({ projectId, query: trimmed, limit: 8 })
    setRunning(false)
    if (result.ok) setHits(result.data.results)
    else setError(describeError(result.error))
  }

  const attach = async (fileId: string): Promise<void> => {
    setBusyId(fileId)
    await onAttach(fileId)
    setBusyId(null)
  }

  return (
    <Dialog
      open={open}
      title="Attach an existing document"
      subtitle="Search the project and put a document on this ticket."
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
      <form
        className="search"
        onSubmit={(event) => {
          event.preventDefault()
          void run()
        }}
      >
        <input
          className="search__input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="What is the document about?"
          aria-label="Search the project"
          autoFocus
        />
        <button type="submit" className="btn btn--sm" disabled={running}>
          {running ? <Spinner label="Searching" /> : null}
          Search
        </button>
      </form>

      {error ? <div className="notice notice--error">{error}</div> : null}

      {hits.length === 0 && !running && !error ? (
        <p className="side__empty">
          Search matches folder descriptions and document text locally — no model is called.
        </p>
      ) : null}

      <ul className="ticket-file-list">
        {hits.map((hit) => {
          const already = attachedIds.has(hit.file_id)
          return (
            <li key={hit.file_id} className="ticket-file">
              <div className="ticket-file__open">
                <span className="ticket-file__name">{hit.name}</span>
                <span className="ticket-file__path">
                  {hit.directory_path || 'project root'} · match {scoreText(hit.score)}
                </span>
                {hit.excerpt ? <span className="ticket-file__excerpt">{hit.excerpt}</span> : null}
              </div>
              <button
                type="button"
                className="btn btn--sm"
                disabled={already || busyId === hit.file_id}
                onClick={() => void attach(hit.file_id)}
              >
                {already ? 'Attached' : busyId === hit.file_id ? <Spinner label="Attaching" /> : 'Attach'}
              </button>
            </li>
          )
        })}
      </ul>
    </Dialog>
  )
}

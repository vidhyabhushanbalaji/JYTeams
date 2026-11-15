import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'

import type { FileSaved, PlacementResult, SearchHit } from '@shared/types'

import { describeError } from '../lib/errors'
import { fileNodeId } from '../lib/focusGraph'
import { focusForFile, type TicketFocus } from '../lib/ticketFocus'
import { stepIndex } from '../lib/tickets'
import { useFocusGraph } from '../state/useFocusGraph'
import { useSearch } from '../state/useSearch'
import { AddDocumentFlow } from './AddDocumentFlow'
import { DocumentSheet } from './DocumentSheet'
import { GraphCanvas } from './GraphCanvas'
import { Inspector } from './Inspector'
import { SearchResults } from './SearchResults'
import { Spinner } from './primitives'

export function ProjectScreen({
  projectId,
  ticketFocus,
  onClearTicketFocus,
  onOpenSettings,
  notify
}: {
  projectId: string
  /** The files a ticket asked the graph to highlight, and which one to open first. */
  ticketFocus: TicketFocus | null
  onClearTicketFocus: () => void
  onOpenSettings: () => void
  notify: (message: string, tone?: 'info' | 'error') => void
}) {
  const graph = useFocusGraph(projectId)
  const search = useSearch(projectId)
  const [side, setSide] = useState<'inspector' | 'search'>('inspector')
  const [query, setQuery] = useState('')
  const [adding, setAdding] = useState(false)
  const [openFileId, setOpenFileId] = useState<string | null>(null)
  const [matchIndex, setMatchIndex] = useState(0)
  const appliedFocus = useRef<string | null>(null)

  const view = graph.view

  const selected = useMemo(
    () => view?.nodes.find((node) => node.id === graph.selectedId) ?? null,
    [view, graph.selectedId]
  )

  const hits = useMemo(() => {
    const found = new Set<string>()
    for (const hit of search.results?.results ?? []) found.add(fileNodeId(hit.file_id))
    for (const target of ticketFocus?.targets ?? []) found.add(fileNodeId(target.fileId))
    return found
  }, [search.results, ticketFocus])

  // A ticket hands the graph a set of files: open the one that was pressed, highlight the rest.
  const revealTicketFocus = graph.revealPath
  const focusNode = graph.focusNode
  useEffect(() => {
    if (!ticketFocus || graph.status !== 'ready') return
    const key = `${ticketFocus.label}|${ticketFocus.entryFileId}`
    if (appliedFocus.current === key) return
    const entry =
      focusForFile(ticketFocus, ticketFocus.entryFileId) ?? ticketFocus.targets[0] ?? null
    if (!entry) return
    appliedFocus.current = key
    setMatchIndex(Math.max(0, ticketFocus.targets.findIndex((item) => item.fileId === entry.fileId)))
    void (async () => {
      await revealTicketFocus(entry.directoryPath)
      focusNode(fileNodeId(entry.fileId))
    })()
  }, [ticketFocus, graph.status, revealTicketFocus, focusNode])

  const stepMatch = async (direction: 1 | -1): Promise<void> => {
    if (!ticketFocus || ticketFocus.targets.length === 0) return
    const next = stepIndex(matchIndex, ticketFocus.targets.length, direction)
    setMatchIndex(next)
    const target = ticketFocus.targets[next]
    await graph.revealPath(target.directoryPath)
    graph.focusNode(fileNodeId(target.fileId))
  }

  useEffect(() => {
    if (!graph.actionError) return
    notify(describeError(graph.actionError), 'error')
    graph.clearActionError()
  }, [graph.actionError, graph.clearActionError, notify])

  const submitSearch = (event: FormEvent): void => {
    event.preventDefault()
    setSide('search')
    void search.run(query)
  }

  const openFolder = (refId: string): void => {
    setOpenFileId(null)
    graph.select(null)
    void graph.enter(refId)
  }

  const openHit = async (hit: SearchHit): Promise<void> => {
    setOpenFileId(null)
    await graph.revealPath(hit.directory_path)
    graph.focusNode(fileNodeId(hit.file_id))
  }

  const saved = (result: FileSaved): void => {
    notify(`Saved ${result.name}.`)
    void graph.refreshCurrent()
  }

  const placed = async (result: PlacementResult): Promise<void> => {
    notify(`Added ${result.file.name} to ${result.directory_path || 'the project root'}.`)
    await graph.revealPath(result.directory_path)
    await graph.refreshCurrent()
    graph.focusNode(fileNodeId(result.file.id))
  }

  const isEmpty = view !== null && view.nodes.length <= 1

  return (
    <>
      <header className="topbar">
        <button
          type="button"
          className="topbar__back btn btn--ghost btn--sm"
          onClick={graph.back}
          disabled={graph.stack.length <= 1}
          title={graph.stack.length <= 1 ? 'You are at the project root' : 'Back to the previous folder'}
        >
          {'\u2190'} Back
        </button>

        <nav className="crumbs" aria-label="Folder path">
          {graph.stack.map((crumb, index) => {
            const isLast = index === graph.stack.length - 1
            return (
              <span key={crumb.id} className="crumbs__item">
                {index > 0 ? (
                  <span className="crumb__sep" aria-hidden="true">
                    /
                  </span>
                ) : null}
                <button
                  type="button"
                  className={`crumb${isLast ? ' crumb--current' : ''}`}
                  onClick={() => graph.jumpTo(index)}
                  disabled={isLast}
                  aria-current={isLast ? 'page' : undefined}
                  title={crumb.path || 'Project root'}
                >
                  {crumb.name}
                </button>
              </span>
            )
          })}
        </nav>

        <div className="topbar__grow" />

        <form className="search" onSubmit={submitSearch} role="search">
          <input
            className="search__input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search this project"
            aria-label="Search this project"
          />
          <button type="submit" className="btn btn--sm" disabled={search.status === 'running'}>
            Search
          </button>
        </form>

        <div className="topbar__actions">
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => void graph.tidy()}>
            Tidy layout
          </button>
          <button type="button" className="btn btn--primary btn--sm" onClick={() => setAdding(true)}>
            Add document
          </button>
        </div>
      </header>

      <div className="workspace">
        <div className="workspace__canvas">
          {ticketFocus ? (
            <div className="ticket-strip">
              <span className="ticket-strip__label">{ticketFocus.label}</span>
              <span className="ticket-strip__count">
                {ticketFocus.targets.length > 0
                  ? `${matchIndex + 1} of ${ticketFocus.targets.length} ticket files`
                  : 'no files on this ticket'}
              </span>
              <div className="ticket-strip__actions">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => void stepMatch(-1)}
                  disabled={ticketFocus.targets.length < 2}
                  aria-label="Previous ticket file"
                >
                  {'\u2039'}
                </button>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => void stepMatch(1)}
                  disabled={ticketFocus.targets.length < 2}
                  aria-label="Next ticket file"
                >
                  {'\u203a'}
                </button>
                <button type="button" className="btn btn--ghost btn--sm" onClick={onClearTicketFocus}>
                  Clear
                </button>
              </div>
            </div>
          ) : null}

          {graph.status === 'loading' ? (
            <div className="canvas__state">
              <Spinner label="Opening the project" />
              <p className="canvas__state-text">Reading the top of the tree.</p>
            </div>
          ) : null}

          {graph.status === 'error' ? (
            <div className="canvas__state">
              <p className="canvas__state-title">This project could not be opened</p>
              <p className="canvas__state-text">
                {graph.error ? describeError(graph.error) : 'The backend gave no reason.'}
              </p>
              <div className="screen__actions" style={{ marginLeft: 0 }}>
                <button type="button" className="btn" onClick={() => void graph.reload()}>
                  Try again
                </button>
                <button type="button" className="btn btn--ghost" onClick={onOpenSettings}>
                  Settings
                </button>
              </div>
            </div>
          ) : null}

          {graph.status === 'ready' && view ? (
            isEmpty ? (
              <div className="canvas__state">
                <p className="canvas__state-title">This folder is empty</p>
                <p className="canvas__state-text">
                  Add a document and it will be placed in the folder you choose.
                </p>
                <button type="button" className="btn btn--primary" onClick={() => setAdding(true)}>
                  Add a document
                </button>
              </div>
            ) : (
              <>
                <div className="canvas">
                  <GraphCanvas
                    model={view}
                    placements={graph.placements}
                    graphKey={graph.graphKey}
                    viewKey={graph.viewKey}
                    selectedId={graph.selectedId}
                    focus={graph.focus}
                    busyId={graph.busyId}
                    hits={hits}
                    dimmed={
                      (search.results !== null && search.results.results.length > 0) ||
                      Boolean(ticketFocus?.targets.length)
                    }
                    onSelect={graph.select}
                    onOpen={openFolder}
                    onOpenFile={setOpenFileId}
                    onMove={graph.move}
                  />
                </div>
                <p className="canvas__hint">
                  Click a card to read it · double-click a document to open it · drag to rearrange
                </p>
              </>
            )
          ) : null}

          <DocumentSheet
            fileId={openFileId}
            onClose={() => setOpenFileId(null)}
            onSaved={saved}
          />
        </div>

        <aside className="workspace__side">
          <div className="side__head">
            <span className="side__title">{side === 'search' ? 'Search results' : 'Details'}</span>
            <span style={{ flex: 1 }} />
            {side === 'search' ? (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  search.clear()
                  setSide('inspector')
                }}
              >
                Clear
              </button>
            ) : null}
          </div>

          {side === 'search' ? (
            <SearchResults
              status={search.status}
              results={search.results}
              error={search.error}
              onOpenHit={(hit) => void openHit(hit)}
            />
          ) : (
            <Inspector node={selected ?? view?.centre ?? null} onOpenFile={setOpenFileId} />
          )}
        </aside>
      </div>

      <AddDocumentFlow
        open={adding}
        projectId={projectId}
        onClose={() => setAdding(false)}
        onPlaced={(result) => void placed(result)}
      />
    </>
  )
}
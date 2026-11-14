import { useEffect, useMemo, useState, type FormEvent } from 'react'

import type { PlacementResult, SearchHit } from '@shared/types'

import { describeError } from '../lib/errors'
import { directoryNodeId, fileNodeId } from '../lib/treeToGraph'
import { useProjectGraph } from '../state/useProjectGraph'
import { useSearch } from '../state/useSearch'
import { AddDocumentFlow } from './AddDocumentFlow'
import { GraphCanvas } from './GraphCanvas'
import { Inspector } from './Inspector'
import { SearchResults } from './SearchResults'
import { Spinner } from './primitives'

export function ProjectScreen({
  projectId,
  onBack,
  onOpenSettings,
  notify
}: {
  projectId: string
  onBack: () => void
  onOpenSettings: () => void
  notify: (message: string, tone?: 'info' | 'error') => void
}) {
  const graph = useProjectGraph(projectId)
  const search = useSearch(projectId)
  const [side, setSide] = useState<'inspector' | 'search'>('inspector')
  const [query, setQuery] = useState('')
  const [adding, setAdding] = useState(false)

  const model = graph.model
  const selected = useMemo(
    () => model?.nodes.find((node) => node.id === graph.selectedId) ?? null,
    [model, graph.selectedId]
  )

  const hits = useMemo(() => {
    const found = new Set<string>()
    for (const hit of search.results?.results ?? []) found.add(fileNodeId(hit.file_id))
    return found
  }, [search.results])

  const byPath = useMemo(() => {
    const map = new Map<string, string>()
    for (const directory of graph.directoryIndex.values()) map.set(directory.path, directory.id)
    return map
  }, [graph.directoryIndex])

  const visited = useMemo(() => {
    const opened = new Set<string>()
    for (const path of search.results?.opened_directories ?? []) {
      const id = byPath.get(path)
      if (id) opened.add(directoryNodeId(id))
    }
    return opened
  }, [search.results, byPath])

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

  const openHit = async (hit: SearchHit): Promise<void> => {
    await graph.revealDirectory(hit.directory_path)
    graph.focusNode(fileNodeId(hit.file_id))
  }

  const placed = async (result: PlacementResult): Promise<void> => {
    notify(`Added ${result.file.name} to ${result.directory_path || 'the project root'}.`)
    await graph.refresh(result.directory_path)
    graph.focusNode(fileNodeId(result.file.id))
  }

  const empty = model !== null && model.nodes.length <= 1

  return (
    <>
      <header className="topbar">
        <button type="button" className="btn btn--ghost btn--sm" onClick={onBack}>
          {'\u2190'} Projects
        </button>

        <div className="topbar__titles">
          <span className="topbar__title">{graph.project?.name ?? 'Opening project'}</span>
          <span className="topbar__crumb">
            {selected ? selected.path || '(project root)' : `${model?.nodes.length ?? 0} cards drawn`}
          </span>
        </div>

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
          {graph.status === 'loading' ? (
            <div className="canvas__state">
              <Spinner label="Opening the project" />
              <p className="canvas__state-text">Reading the tree and its descriptions.</p>
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

          {graph.status === 'ready' && model ? (
            empty ? (
              <div className="canvas__state">
                <p className="canvas__state-title">Nothing in this tree yet</p>
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
                    model={model}
                    placements={graph.placements}
                    selectedId={graph.selectedId}
                    focus={graph.focus}
                    busyId={graph.busyId}
                    hits={hits}
                    visited={visited}
                    dimmed={search.results !== null && search.results.results.length > 0}
                    onSelect={graph.select}
                    onToggle={(refId) => void graph.toggle(refId)}
                    onMove={graph.move}
                  />
                </div>
                <p className="canvas__hint">
                  Drag a card to move it · scroll to zoom · chevron to expand a folder
                </p>
              </>
            )
          ) : null}
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
            <Inspector node={selected} />
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
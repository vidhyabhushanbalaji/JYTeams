import type { ApiError, SearchHit, SearchResults as SearchPayload } from '@shared/types'

import { describeError } from '../lib/errors'
import type { SearchStatus } from '../state/useSearch'
import { Spinner } from './primitives'

export function SearchResults({
  status,
  results,
  error,
  onOpenHit
}: {
  status: SearchStatus
  results: SearchPayload | null
  error: ApiError | null
  onOpenHit: (hit: SearchHit) => void
}) {
  if (status === 'idle') {
    return (
      <div className="side__body">
        <div className="side__section">
          <span className="side__label">Search</span>
          <p className="side__empty">
            Ask for the document you need, in your own words. The project is walked folder by
            folder and the answers come back ranked, with the reason each one matched.
          </p>
        </div>
      </div>
    )
  }

  if (status === 'running') {
    return (
      <div className="side__body">
        <div className="side__section">
          <span className="side__label">Searching</span>
          <p className="side__text">
            <Spinner label="Searching" /> <span style={{ marginLeft: 8 }}>Walking the tree.</span>
          </p>
          <p className="side__empty">
            One model call per folder it opens, so this can take a little while on a large project.
          </p>
        </div>
      </div>
    )
  }

  if (status === 'error' || !results) {
    return (
      <div className="side__body">
        <div className="side__section">
          <span className="side__label">Search</span>
          <p className="side__text">{error ? describeError(error) : 'The search did not run.'}</p>
        </div>
      </div>
    )
  }

  const { traversal } = results
  const flags = [
    traversal.fallback_used ? 'whole-tree fallback' : '',
    traversal.budget_exhausted ? 'budget exhausted' : '',
    traversal.degraded ? 'degraded model call' : ''
  ].filter(Boolean)

  return (
    <>
      <p className="search__meta">
        {results.results.length} {results.results.length === 1 ? 'answer' : 'answers'} for{' '}
        {`"${results.query}"`}
        <br />
        {traversal.directories_opened} folders opened · {traversal.documents_considered} documents
        ranked · {traversal.model}
        {flags.length > 0 ? ` · ${flags.join(' · ')}` : ''}
      </p>
      <div className="hits">
        {results.results.length === 0 ? (
          <div className="side__body">
            <p className="side__empty">
              Nothing answered that. Try describing the document's subject rather than its filename -
              the search reads summaries, not file contents.
            </p>
          </div>
        ) : null}
        {results.results.map((hit) => (
          <button key={hit.file_id} type="button" className="hit" onClick={() => onOpenHit(hit)}>
            <span className="hit__top">
              <span className="hit__name">{hit.name}</span>
              <span className="hit__score">{hit.score.toFixed(2)}</span>
            </span>
            <span className="hit__path">{hit.path}</span>
            <span className="hit__reason">{hit.reason}</span>
          </button>
        ))}
      </div>
    </>
  )
}
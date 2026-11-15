import type { ApiError, SearchHit, SearchResults as SearchPayload } from '@shared/types'

import { describeError } from '../lib/errors'
import { evidenceLine, searchFlags, searchMeta, visibleTerms } from '../lib/payloads'
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
            Ask for the document you need, in your own words. Folders are scored from their
            descriptions and the documents inside them are matched against their own text — no
            model is called.
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
            Folders are scored locally and only matching ones are opened, so a search costs no model
            calls — reading many documents is what takes the time.
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
  const flags = searchFlags(traversal)

  return (
    <div className="side__scroll">
      <p className="search__meta">
        {results.results.length} {results.results.length === 1 ? 'answer' : 'answers'} for{' '}
        {`"${results.query}"`}
        <br />
        {searchMeta(traversal)}
        {flags.length > 0 ? ` · ${flags.join(' · ')}` : ''}
      </p>
      <div className="hits">
        {results.results.length === 0 ? (
          <p className="side__empty side__pad">
            Nothing answered that. The search matches the words in each document and its folder
            descriptions, so try a term the documentation itself would use.
          </p>
        ) : null}
        {results.results.map((hit) => (
          <button key={hit.file_id} type="button" className="hit" onClick={() => onOpenHit(hit)}>
            <span className="hit__top">
              <span className="hit__name">{hit.name}</span>
              <span className="hit__score">{hit.score.toFixed(2)}</span>
            </span>
            <span className="hit__path">{hit.path}</span>
            <span className="hit__reason">{evidenceLine(hit)}</span>
            {hit.matched_terms.length > 0 ? (
              <span className="chips">
                {visibleTerms(hit.matched_terms).map((term) => (
                  <span key={term} className="chip">
                    {term}
                  </span>
                ))}
              </span>
            ) : null}
          </button>
        ))}
      </div>
    </div>
  )
}
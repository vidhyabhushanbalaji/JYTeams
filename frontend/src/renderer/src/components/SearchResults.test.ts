import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import type { SearchResults as SearchPayload } from '@shared/types'

import { SearchResults } from './SearchResults'

// The payload shape is the one documented in backend/README.md ("Graph AI Search endpoints").
const RESULTS: SearchPayload = {
  query: 'how do I roll back a bad production release',
  context: '',
  project_id: '014c45b7',
  results: [
    {
      file_id: 'ff230d49',
      name: 'rollback-deployment.md',
      path: 'guides/rollback-deployment.md',
      directory_id: 'dd473be5',
      directory_path: 'guides',
      score: 0.71,
      matched_terms: ['deployment', 'release', 'rollback'],
      excerpt: 'This document provides a step-by-step guide for performing a Helm rollback…'
    }
  ],
  directories: [
    {
      directory_id: 'dd473be5',
      path: 'guides',
      name: 'guides',
      depth: 1,
      score: 0.42,
      matched_terms: ['deployment', 'release']
    }
  ],
  opened_directories: ['', 'guides'],
  traversal: {
    directories_visited: 2,
    directories_opened: 2,
    documents_considered: 6,
    files_read: 3,
    fallback_used: false,
    degraded: false,
    budget_exhausted: false,
    scorer_version: 'local-1',
    duration_ms: 41
  }
}

function render(results: SearchPayload): string {
  return renderToStaticMarkup(
    createElement(SearchResults, {
      status: 'done',
      results,
      error: null,
      onOpenHit: () => undefined
    })
  )
}

describe('SearchResults', () => {
  it('shows the evidence the API now returns, not the removed reason', () => {
    const markup = render(RESULTS)

    expect(markup).toContain('guides/rollback-deployment.md')
    expect(markup).toContain('This document provides a step-by-step guide')
    expect(markup).toContain('deployment')
  })

  it('keeps the hits in a scrollable panel, with the summary line pinned', () => {
    const markup = render(RESULTS)

    // The panel head is fixed, so the results themselves own the scroll region.
    expect(markup).toContain('class="side__scroll"')
    expect(markup).toContain('class="search__meta"')
  })

  it('still scrolls when nothing matched', () => {
    const markup = render({ ...RESULTS, results: [] })

    expect(markup).toContain('class="side__scroll"')
    expect(markup).toContain('side__pad')
    expect(markup).toContain('Nothing answered that')
  })

  it('describes the local walk from the traversal fields', () => {
    const markup = render(RESULTS)

    expect(markup).toContain('2 of 2 folders opened')
    expect(markup).toContain('3 documents read of 6 considered')
    expect(markup).toContain('local-1')
  })

  it('falls back to the matched terms when a document has no excerpt', () => {
    const markup = render({
      ...RESULTS,
      results: [{ ...RESULTS.results[0], excerpt: '' }]
    })

    expect(markup).toContain('Matched deployment, release, rollback')
  })

  it('names a degraded read instead of blaming a model', () => {
    const markup = render({
      ...RESULTS,
      traversal: { ...RESULTS.traversal, degraded: true }
    })

    expect(markup).toContain('some documents could not be read')
    expect(markup).not.toContain('model call')
  })
})

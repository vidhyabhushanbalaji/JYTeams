import { describe, expect, it } from 'vitest'

import type { DocumentBrief, ScanInfo, SearchHit, SearchTraversal } from '@shared/types'

import {
  documentPreview,
  evidenceLine,
  searchFlags,
  searchMeta,
  scanSummary,
  visibleTerms
} from './payloads'

// Fixtures mirror backend/README.md ("Graph Add endpoints", "Graph AI Search endpoints") and
// the pydantic models, so a renamed field fails here before it can blank a panel.
const SCAN: ScanInfo = {
  folders_scored: 128,
  threshold: 0.18,
  scorer_version: 'local-1'
}

const FILE: DocumentBrief = {
  name: 'rollback-deployment.md',
  size_bytes: 4096,
  content_sha256: '9f2c',
  preview: '  This document explains how to roll back a bad production release.  '
}

const TRAVERSAL: SearchTraversal = {
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

const HIT: SearchHit = {
  file_id: 'ff230d49',
  name: 'rollback-deployment.md',
  path: 'guides/rollback-deployment.md',
  directory_id: 'dd473be5',
  directory_path: 'guides',
  score: 0.71,
  matched_terms: ['deployment', 'release', 'rollback'],
  excerpt: 'This document provides a step-by-step guide for performing a Helm rollback…'
}

describe('documentPreview', () => {
  it('uses the stored preview, trimmed', () => {
    expect(documentPreview(FILE)).toBe(
      'This document explains how to roll back a bad production release.'
    )
  })

  it('falls back to the file name when there is no text to preview', () => {
    expect(documentPreview({ ...FILE, preview: '   ' })).toBe(FILE.name)
  })
})

describe('scanSummary', () => {
  it('reports what the local scan cost', () => {
    expect(scanSummary(SCAN)).toBe(
      'Scored 128 folders locally · threshold 0.18 · local-1'
    )
  })

  it('singularises one folder and keeps two decimals', () => {
    expect(scanSummary({ ...SCAN, folders_scored: 1, threshold: 0.2 })).toBe(
      'Scored 1 folder locally · threshold 0.20 · local-1'
    )
  })
})

describe('searchMeta', () => {
  it('describes the walk from the traversal fields the API returns', () => {
    expect(searchMeta(TRAVERSAL)).toBe(
      '2 of 2 folders opened · 3 documents read of 6 considered · 41 ms · local-1'
    )
  })

  it('never prints a negative duration', () => {
    expect(searchMeta({ ...TRAVERSAL, duration_ms: -5 })).toContain('0 ms')
  })
})

describe('searchFlags', () => {
  it('says nothing when the walk was clean', () => {
    expect(searchFlags(TRAVERSAL)).toEqual([])
  })

  it('names each improvisation', () => {
    expect(searchFlags({ ...TRAVERSAL, fallback_used: true })).toEqual(['whole-tree sweep'])
    expect(searchFlags({ ...TRAVERSAL, budget_exhausted: true })).toEqual(['read budget reached'])
    expect(searchFlags({ ...TRAVERSAL, degraded: true })).toEqual([
      'some documents could not be read'
    ])
  })
})

describe('evidenceLine', () => {
  it('shows the excerpt the backend cut from the document', () => {
    expect(evidenceLine(HIT)).toBe(HIT.excerpt)
  })

  it('falls back to the matched terms, then to a neutral line', () => {
    expect(evidenceLine({ ...HIT, excerpt: '  ' })).toBe(
      'Matched deployment, release, rollback'
    )
    expect(evidenceLine({ ...HIT, excerpt: '', matched_terms: [] })).toBe(
      'Matched on the document text.'
    )
  })
})

describe('visibleTerms', () => {
  it('caps the chips at six terms', () => {
    const terms = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    expect(visibleTerms(terms)).toEqual(['a', 'b', 'c', 'd', 'e', 'f'])
  })

  it('leaves shorter lists untouched', () => {
    expect(visibleTerms(HIT.matched_terms)).toEqual(HIT.matched_terms)
  })
})

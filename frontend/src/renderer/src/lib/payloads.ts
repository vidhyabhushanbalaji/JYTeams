/**
 * Pure adapters between the API payloads and the words the panels show.
 *
 * They stay small and side-effect free so `payloads.test.ts` can feed them the exact JSON
 * published in `backend/README.md`: a backend field rename then fails a test instead of
 * blanking a panel at runtime.
 */

import type { DocumentBrief, ScanInfo, SearchHit, SearchTraversal } from '@shared/types'

/** Long enough to explain a match, short enough not to become a second result list. */
const MAX_TERMS = 6

/** The model-free preview Graph Add keeps with a suggestion. */
export function documentPreview(file: DocumentBrief): string {
  return file.preview.trim() || file.name
}

/** What the local folder scan cost — no model call, so say so. */
export function scanSummary(scan: ScanInfo): string {
  const folders = scan.folders_scored === 1 ? 'folder' : 'folders'
  return `Scored ${scan.folders_scored} ${folders} locally · threshold ${decimal(
    scan.threshold
  )} · ${scan.scorer_version}`
}

/** What the read-only search walk actually did. */
export function searchMeta(traversal: SearchTraversal): string {
  return [
    `${traversal.directories_opened} of ${traversal.directories_visited} folders opened`,
    `${traversal.files_read} documents read of ${traversal.documents_considered} considered`,
    `${Math.max(0, Math.round(traversal.duration_ms))} ms`,
    traversal.scorer_version
  ].join(' · ')
}

/** The warnings worth surfacing beside a set of search results. */
export function searchFlags(traversal: SearchTraversal): string[] {
  return [
    traversal.fallback_used ? 'whole-tree sweep' : '',
    traversal.budget_exhausted ? 'read budget reached' : '',
    traversal.degraded ? 'some documents could not be read' : ''
  ].filter(Boolean)
}

/** Why a document matched: a faithful excerpt, or the terms that scored it. */
export function evidenceLine(hit: SearchHit): string {
  const excerpt = hit.excerpt.trim()
  if (excerpt) return excerpt
  if (hit.matched_terms.length > 0) return `Matched ${termList(hit.matched_terms)}`
  return 'Matched on the document text.'
}

/** The terms to show as chips, capped so a long query cannot flood the panel. */
export function visibleTerms(terms: string[]): string[] {
  return terms.slice(0, MAX_TERMS)
}

function termList(terms: string[]): string {
  return visibleTerms(terms).join(', ')
}

function decimal(value: number): string {
  return Number.isFinite(value) ? value.toFixed(2) : '0.00'
}

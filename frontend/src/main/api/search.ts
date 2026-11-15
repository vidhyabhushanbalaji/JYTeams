/** Graph AI Search is one read: no model is called, but a search may read many documents. */

import type { SearchResults } from '../../shared/types'
import { LONG_TIMEOUT_MS, request } from './client'

export async function searchProject(input: {
  projectId: string
  query: string
  limit: number
}): Promise<SearchResults> {
  const params = new URLSearchParams({ q: input.query, limit: String(input.limit) })
  return request<SearchResults>(
    `/api/graph-ai-search/projects/${encodeURIComponent(input.projectId)}/search?${params.toString()}`,
    { timeoutMs: LONG_TIMEOUT_MS }
  )
}
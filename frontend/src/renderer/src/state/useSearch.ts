import { useCallback, useState } from 'react'

import type { ApiError, SearchResults } from '@shared/types'

export type SearchStatus = 'idle' | 'running' | 'done' | 'error'

export function useSearch(projectId: string) {
  const [status, setStatus] = useState<SearchStatus>('idle')
  const [results, setResults] = useState<SearchResults | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  const run = useCallback(
    async (query: string) => {
      const trimmed = query.trim()
      if (trimmed.length < 3) {
        setResults(null)
        setStatus('error')
        setError({ status: 400, message: 'Type at least three characters to search.', detail: null })
        return
      }
      setStatus('running')
      setError(null)
      const result = await window.jyteams.search.run({ projectId, query: trimmed })
      if (result.ok) {
        setResults(result.data)
        setStatus('done')
      } else {
        setResults(null)
        setError(result.error)
        setStatus('error')
      }
    },
    [projectId]
  )

  const clear = useCallback(() => {
    setStatus('idle')
    setResults(null)
    setError(null)
  }, [])

  return { status, results, error, run, clear }
}
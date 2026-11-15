/**
 * The composer's `@` suggestions: documents, folders and tickets of the current project.
 *
 * Typing is debounced (160 ms) so a fast typist costs one read per word, not one per keystroke.
 */

import { useEffect, useState } from 'react'

import type { ApiError, MentionTarget } from '@shared/types'

const DEBOUNCE_MS = 160

export function useMentionTargets(projectId: string | null, query: string, enabled: boolean) {
  const [targets, setTargets] = useState<MentionTarget[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (!enabled || !projectId) {
      setTargets([])
      setLoading(false)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    const timer = setTimeout(() => {
      void (async () => {
        const result = await window.jyteams.chat.mentionTargets({
          projectId,
          query,
          limit: 20
        })
        if (cancelled) return
        if (result.ok) {
          setTargets(result.data)
          setError(null)
        } else {
          setTargets([])
          setError(result.error)
        }
        setLoading(false)
      })()
    }, DEBOUNCE_MS)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [projectId, query, enabled])

  return { targets, loading, error }
}

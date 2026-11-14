import { useCallback, useEffect, useState } from 'react'

import type { ApiError, Project } from '@shared/types'

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    const result = await window.jyteams.projects.list()
    if (result.ok) {
      setProjects(result.data)
    } else {
      setProjects([])
      setError(result.error)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { projects, loading, error, reload }
}
/** Where each card sits, per project, in the main process (see src/main/layout.ts). */

import { useCallback, useEffect, useState } from 'react'

import type { XYPosition } from '@shared/types'

export function usePositions(projectId: string) {
  const [positions, setPositions] = useState<Record<string, XYPosition>>({})
  const [nonce, setNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setPositions({})
    void window.jyteams.layout.load(projectId).then((stored) => {
      if (!cancelled) setPositions(stored)
    })
    return () => {
      cancelled = true
    }
  }, [projectId])

  const move = useCallback(
    (nodeId: string, position: XYPosition) => {
      setPositions((current) => {
        const next = { ...current, [nodeId]: position }
        void window.jyteams.layout.save(projectId, next)
        return next
      })
    },
    [projectId]
  )

  const reset = useCallback(async () => {
    await window.jyteams.layout.clear(projectId)
    setPositions({})
    setNonce((value) => value + 1)
  }, [projectId])

  return { positions, move, reset, nonce }
}
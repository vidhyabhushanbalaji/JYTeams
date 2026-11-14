/**
 * Where each card sits, remembered per view.
 *
 * Keys are `viewId::nodeId`, so drilling into a folder and coming back restores that view
 * exactly as you left it - drags included. One flat map keeps the file written by the main
 * process (userData/layouts) exactly as it was.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import type { XYPosition } from '@shared/types'

const SEPARATOR = '::'

export function positionsFor(
  stored: Record<string, XYPosition>,
  viewKey: string
): Record<string, XYPosition> {
  const prefix = `${viewKey}${SEPARATOR}`
  const view: Record<string, XYPosition> = {}
  for (const [key, value] of Object.entries(stored)) {
    if (key.startsWith(prefix)) view[key.slice(prefix.length)] = value
  }
  return view
}

export function usePositions(projectId: string) {
  const [stored, setStored] = useState<Record<string, XYPosition>>({})
  const storedRef = useRef(stored)
  storedRef.current = stored

  useEffect(() => {
    let cancelled = false
    setStored({})
    void window.jyteams.layout.load(projectId).then((loaded) => {
      if (!cancelled) setStored(loaded)
    })
    return () => {
      cancelled = true
    }
  }, [projectId])

  const move = useCallback(
    (viewKey: string, nodeId: string, position: XYPosition) => {
      setStored((current) => {
        const next = { ...current, [`${viewKey}${SEPARATOR}${nodeId}`]: position }
        void window.jyteams.layout.save(projectId, next)
        return next
      })
    },
    [projectId]
  )

  const clearView = useCallback(
    async (viewKey: string) => {
      const prefix = `${viewKey}${SEPARATOR}`
      const next: Record<string, XYPosition> = {}
      for (const [key, value] of Object.entries(storedRef.current)) {
        if (!key.startsWith(prefix)) next[key] = value
      }
      await window.jyteams.layout.save(projectId, next)
      setStored(next)
    },
    [projectId]
  )

  return { stored, move, clearView }
}
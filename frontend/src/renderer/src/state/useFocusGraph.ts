/**
 * The drill-down model behind the wheel.
 *
 * One folder is "current"; it becomes the centre card and the view holds its direct files
 * and its immediate subfolders - nothing else. Pressing a folder pushes it onto a small
 * stack (the breadcrumb), Back pops it, and each level is one GET /directories/{id},
 * cached for the session so returning is instant.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { ApiError, DirectoryChildren, Project, XYPosition } from '@shared/types'

import { buildFocusView, type FocusViewModel } from '../lib/focusGraph'
import { treePositions } from '../lib/treeLayout'
import { positionsFor, usePositions } from './usePositions'

export interface Crumb {
  id: string
  name: string
  path: string
}

export interface FocusRequest {
  nodeId: string
  nonce: number
}

interface FocusState {
  status: 'loading' | 'ready' | 'error'
  project: Project | null
  stack: Crumb[]
  cache: Record<string, DirectoryChildren>
  error: ApiError | null
  revision: number
}

const EMPTY: FocusState = {
  status: 'loading',
  project: null,
  stack: [],
  cache: {},
  error: null,
  revision: 0
}

export function useFocusGraph(projectId: string) {
  const [state, setState] = useState<FocusState>(EMPTY)
  const stateRef = useRef(state)
  stateRef.current = state

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focus, setFocus] = useState<FocusRequest | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  const positions = usePositions(projectId)
  const moveCard = positions.move
  const clearCards = positions.clearView

  const open = useCallback(async () => {
    setState({ ...EMPTY })
    const projectResult = await window.jyteams.projects.get(projectId)
    if (!projectResult.ok) {
      setState((current) => ({ ...current, status: 'error', error: projectResult.error }))
      return
    }

    const project = projectResult.data
    const rootId = project.root_directory_id
    if (!rootId) {
      setState((current) => ({
        ...current,
        status: 'error',
        error: { status: 409, message: 'This project has no tree yet.', detail: null }
      }))
      return
    }

    const rootResult = await window.jyteams.projects.directory(rootId)
    if (!rootResult.ok) {
      setState((current) => ({ ...current, status: 'error', project, error: rootResult.error }))
      return
    }

    const root = rootResult.data
    const crumb: Crumb = {
      id: root.directory.id,
      name: project.name || root.directory.name || 'Project root',
      path: root.directory.path
    }
    setState({
      status: 'ready',
      project,
      stack: [crumb],
      cache: { [crumb.id]: root },
      error: null,
      revision: 0
    })
  }, [projectId])

  useEffect(() => {
    void open()
  }, [open])

  const current = state.stack.length > 0 ? state.stack[state.stack.length - 1] : null
  const payload = current ? state.cache[current.id] ?? null : null
  const viewKey = current?.id ?? ''

  const view: FocusViewModel | null = useMemo(() => {
    if (!payload) return null
    return buildFocusView({
      directory: payload.directory,
      files: payload.files,
      directories: payload.directories,
      centreLabel: state.project?.name
    })
  }, [payload, state.project?.name])

  const tree = useMemo(() => (view ? treePositions(view) : {}), [view])
  const stored = useMemo(() => positionsFor(positions.stored, viewKey), [positions.stored, viewKey])
  const placements = useMemo(() => ({ ...tree, ...stored }), [tree, stored])

  /** Go into a folder: it becomes the centre. Re-pressing an ancestor acts like Back to it. */
  const enter = useCallback(async (directoryId: string) => {
    const before = stateRef.current
    const existing = before.stack.findIndex((item) => item.id === directoryId)
    if (existing >= 0) {
      if (existing === before.stack.length - 1) return
      const truncated: FocusState = {
        ...before,
        stack: before.stack.slice(0, existing + 1),
        revision: before.revision + 1
      }
      stateRef.current = truncated
      setState(truncated)
      return
    }

    let loaded = before.cache[directoryId]
    if (!loaded) {
      setBusyId(directoryId)
      const result = await window.jyteams.projects.directory(directoryId)
      setBusyId(null)
      if (!result.ok) {
        setActionError(result.error)
        return
      }
      loaded = result.data
    }

    const after = stateRef.current
    const crumb: Crumb = {
      id: loaded.directory.id,
      name: loaded.directory.name || 'Untitled folder',
      path: loaded.directory.path
    }
    const next: FocusState = {
      ...after,
      status: 'ready',
      stack: [...after.stack, crumb],
      cache: { ...after.cache, [directoryId]: loaded },
      error: null,
      revision: after.revision + 1
    }
    stateRef.current = next
    setState(next)
  }, [])

  const back = useCallback(() => {
    const currentState = stateRef.current
    if (currentState.stack.length <= 1) return
    setState({
      ...currentState,
      stack: currentState.stack.slice(0, -1),
      revision: currentState.revision + 1
    })
  }, [])

  const jumpTo = useCallback((index: number) => {
    setState((currentState) => {
      if (index < 0 || index >= currentState.stack.length - 1) return currentState
      return {
        ...currentState,
        stack: currentState.stack.slice(0, index + 1),
        revision: currentState.revision + 1
      }
    })
  }, [])

  /**
   * Open every folder on the way to `path` (what a search hit or a placement reports).
   * Resolves to the directory id at the end of the path.
   */
  const revealPath = useCallback(async (path: string): Promise<string | null> => {
    const before = stateRef.current
    if (before.stack.length === 0) return null

    const root = before.stack[0]
    const cache: Record<string, DirectoryChildren> = { ...before.cache }

    const load = async (id: string): Promise<DirectoryChildren | null> => {
      const cached = cache[id]
      if (cached) return cached
      const result = await window.jyteams.projects.directory(id)
      if (!result.ok) {
        setActionError(result.error)
        return null
      }
      cache[id] = result.data
      return result.data
    }

    let loaded = await load(root.id)
    if (!loaded) return null

    const chain: Crumb[] = [root]
    for (const segment of path.split('/').filter(Boolean)) {
      const child = loaded.directories.find((entry) => entry.name === segment)
      if (!child) return null
      chain.push({ id: child.id, name: child.name, path: child.path })
      loaded = await load(child.id)
      if (!loaded) return null
    }

    const target = chain[chain.length - 1]
    const next: FocusState = {
      ...stateRef.current,
      status: 'ready',
      stack: chain,
      cache,
      error: null,
      revision: stateRef.current.revision + 1
    }
    stateRef.current = next
    setState(next)
    return target.id
  }, [])

  /** Re-read the current folder: a placement changes its files, counts and description. */
  const refreshCurrent = useCallback(async () => {
    const before = stateRef.current
    const target = before.stack[before.stack.length - 1]
    if (!target) return
    const result = await window.jyteams.projects.directory(target.id)
    if (!result.ok) {
      setActionError(result.error)
      return
    }
    const next: FocusState = {
      ...stateRef.current,
      cache: { ...stateRef.current.cache, [target.id]: result.data },
      revision: stateRef.current.revision + 1
    }
    stateRef.current = next
    setState(next)
  }, [])

  const tidy = useCallback(async () => {
    const target = stateRef.current.stack[stateRef.current.stack.length - 1]
    if (!target) return
    await clearCards(target.id)
    setState((currentState) => ({ ...currentState, revision: currentState.revision + 1 }))
  }, [clearCards])

  const move = useCallback(
    (nodeId: string, position: XYPosition) => {
      const target = stateRef.current.stack[stateRef.current.stack.length - 1]
      if (!target) return
      moveCard(target.id, nodeId, position)
    },
    [moveCard]
  )

  const focusNode = useCallback((nodeId: string) => {
    setSelectedId(nodeId)
    setFocus({ nodeId, nonce: Date.now() })
  }, [])

  const clearActionError = useCallback(() => setActionError(null), [])

  return {
    status: state.status,
    project: state.project,
    error: state.error,
    stack: state.stack,
    view,
    placements,
    viewKey,
    graphKey: `${viewKey}:${state.revision}`,
    selectedId,
    focus,
    busyId,
    actionError,
    clearActionError,
    select: setSelectedId,
    focusNode,
    enter,
    back,
    jumpTo,
    revealPath,
    refreshCurrent,
    tidy,
    move,
    reload: open
  }
}

export type ProjectGraph = ReturnType<typeof useFocusGraph>
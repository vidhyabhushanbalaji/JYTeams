/**
 * Everything the graph view needs: the depth-limited tree, the subtrees fetched as nodes are
 * expanded, which nodes are open, where the user put them, and where the view should look.
 *
 * The visible set is derived, never stored: `buildGraph` decides what may be drawn from
 * `tree` + `children` + `expanded`, so the three-level rule cannot drift.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { ApiError, Directory, Project } from '@shared/types'

import { layoutModel, type Positions } from '../lib/layout'
import { buildGraph, indexDirectories, TREE_DEPTH } from '../lib/treeToGraph'
import { usePositions } from './usePositions'

export interface FocusRequest {
  nodeId: string
  nonce: number
}

interface GraphState {
  status: 'loading' | 'ready' | 'error'
  project: Project | null
  tree: Directory | null
  children: Record<string, Directory>
  expanded: Record<string, true>
  error: ApiError | null
}

type Action =
  | { type: 'loading' }
  | { type: 'failed'; error: ApiError }
  | { type: 'loaded'; project: Project; tree: Directory }
  | { type: 'children'; id: string; node: Directory }
  | { type: 'expand'; id: string }
  | { type: 'collapse'; id: string }

const EMPTY: GraphState = {
  status: 'loading',
  project: null,
  tree: null,
  children: {},
  expanded: {},
  error: null
}

function reducer(state: GraphState, action: Action): GraphState {
  switch (action.type) {
    case 'loading':
      return { ...EMPTY }
    case 'failed':
      return { ...state, status: 'error', error: action.error }
    case 'loaded':
      return {
        status: 'ready',
        project: action.project,
        tree: action.tree,
        children: {},
        expanded: { [action.tree.id]: true },
        error: null
      }
    case 'children':
      return { ...state, children: { ...state.children, [action.id]: action.node } }
    case 'expand':
      return { ...state, expanded: { ...state.expanded, [action.id]: true } }
    case 'collapse': {
      const expanded = { ...state.expanded }
      delete expanded[action.id]
      return { ...state, expanded }
    }
    default:
      return state
  }
}

export function useProjectGraph(projectId: string) {
  const [state, setState] = useState<GraphState>(EMPTY)
  const stateRef = useRef(state)
  stateRef.current = state

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focus, setFocus] = useState<FocusRequest | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<ApiError | null>(null)

  const positions = usePositions(projectId)

  const dispatch = useCallback((action: Action) => {
    setState((current) => reducer(current, action))
  }, [])

  const reload = useCallback(async () => {
    dispatch({ type: 'loading' })
    const result = await window.jyteams.projects.tree(projectId, TREE_DEPTH)
    if (result.ok) dispatch({ type: 'loaded', project: result.data.project, tree: result.data.tree })
    else dispatch({ type: 'failed', error: result.error })
  }, [projectId, dispatch])

  useEffect(() => {
    void reload()
  }, [reload])

  const model = useMemo(
    () =>
      state.tree
        ? buildGraph({
            root: state.tree,
            children: state.children,
            expanded: state.expanded,
            rootLabel: state.project?.name
          })
        : null,
    [state.tree, state.children, state.expanded, state.project?.name]
  )

  // Recomputed when the visible set changes, and again after "Tidy" bumps the nonce.
  const autoLayout = useMemo(
    () => (model ? layoutModel(model.nodes, model.edges) : {}),
    [model, positions.nonce]
  )

  const placements: Positions = useMemo(
    () => ({ ...autoLayout, ...positions.positions }),
    [autoLayout, positions.positions]
  )

  const directoryIndex = useMemo(
    () =>
      state.tree
        ? indexDirectories(state.tree, state.children)
        : new Map<string, Directory>(),
    [state.tree, state.children]
  )

  const fetchChildren = useCallback(
    async (directoryId: string): Promise<Directory | null> => {
      const result = await window.jyteams.projects.directory(directoryId)
      if (!result.ok) {
        setActionError(result.error)
        return null
      }
      const merged: Directory = {
        ...result.data.directory,
        files: result.data.files,
        directories: result.data.directories
      }
      dispatch({ type: 'children', id: directoryId, node: merged })
      return merged
    },
    [dispatch]
  )

  const toggle = useCallback(
    async (directoryId: string) => {
      const current = stateRef.current
      if (current.expanded[directoryId]) {
        dispatch({ type: 'collapse', id: directoryId })
        return
      }
      const directory = current.tree
        ? indexDirectories(current.tree, current.children).get(directoryId)
        : null
      if (!directory) return

      const needsFetch =
        !current.children[directoryId] &&
        directory.directories.length === 0 &&
        directory.child_directory_count > 0

      if (needsFetch) {
        setBusyId(directoryId)
        const merged = await fetchChildren(directoryId)
        setBusyId(null)
        if (!merged) return
      }
      dispatch({ type: 'expand', id: directoryId })
    },
    [dispatch, fetchChildren]
  )

  /**
   * Open every folder on the way to `path`, fetching the ones the depth-limited read hid.
   * Resolves to the directory id at the end of the path, or null if it does not exist.
   */
  const revealFrom = useCallback(
    async (base: GraphState, path: string): Promise<string | null> => {
      const root = base.tree
      if (!root) return null

      const segments = path.split('/').filter(Boolean)
      if (segments.length === 0) return root.id

      const known: Record<string, Directory> = { ...base.children, [root.id]: root }
      let parent = root
      let accumulated = ''

      for (const segment of segments) {
        accumulated = accumulated ? `${accumulated}/${segment}` : segment
        let listing = known[parent.id]?.directories ?? []

        if (listing.length === 0 && parent.child_directory_count > 0) {
          const fetched = await fetchChildren(parent.id)
          if (!fetched) return null
          known[parent.id] = fetched
          listing = fetched.directories
        }

        const child = listing.find((entry) => entry.name === segment)
        if (!child) return null

        dispatch({ type: 'expand', id: parent.id })
        known[child.id] = known[child.id] ?? child
        parent = known[child.id]
      }

      dispatch({ type: 'expand', id: parent.id })
      return parent.id
    },
    [dispatch, fetchChildren]
  )

  const revealDirectory = useCallback(
    (path: string) => revealFrom(stateRef.current, path),
    [revealFrom]
  )

  /**
   * Re-read the tree after a placement; folder descriptions and counts have changed above
   * the new file, so cached subtrees are no longer trustworthy. Positions are untouched.
   */
  const refresh = useCallback(
    async (revealPath?: string): Promise<string | null> => {
      const current = stateRef.current
      const projectKey = current.project?.id ?? projectId
      const result = await window.jyteams.projects.tree(projectKey, TREE_DEPTH)
      if (!result.ok) {
        setActionError(result.error)
        return null
      }
      const next: GraphState = {
        status: 'ready',
        project: result.data.project,
        tree: result.data.tree,
        children: {},
        expanded: { [result.data.tree.id]: true },
        error: null
      }
      setState(next)
      stateRef.current = next
      if (!revealPath) return result.data.tree.id
      return revealFrom(next, revealPath)
    },
    [projectId, revealFrom]
  )

  const tidy = useCallback(async () => {
    await positions.reset()
  }, [positions])

  const focusNode = useCallback((nodeId: string) => {
    setSelectedId(nodeId)
    setFocus({ nodeId, nonce: Date.now() })
  }, [])

  const clearActionError = useCallback(() => setActionError(null), [])

  return {
    status: state.status,
    project: state.project,
    error: state.error,
    model,
    placements,
    directoryIndex,
    selectedId,
    focus,
    busyId,
    actionError,
    clearActionError,
    select: setSelectedId,
    move: positions.move,
    focusNode,
    toggle,
    revealDirectory,
    refresh,
    reload,
    tidy
  }
}

export type ProjectGraph = ReturnType<typeof useProjectGraph>
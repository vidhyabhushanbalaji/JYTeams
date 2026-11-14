/**
 * Turning the API tree into the graph the canvas draws.
 *
 * Two rules live here, and nowhere else:
 *   1. Only three tiers of folders are drawn (root + TREE_DEPTH - 1). A deeper folder is
 *      reachable only by expanding one of those, which the user has to ask for.
 *   2. A folder's files appear only once that folder is expanded, so the canvas opens calm.
 *
 * `children` holds subtrees fetched with GET /directories/{id}; wherever one exists it
 * replaces the (possibly depth-truncated) listing that came with the tree read.
 */

import type { Directory, ProjectFile } from '@shared/types'

/** The depth requested from GET /projects/{id}/tree?depth=. 3 = root + two tiers. */
export const TREE_DEPTH = 3

export type GraphNodeKind = 'root' | 'folder' | 'file'

export interface GraphNodeModel {
  /** React Flow id, prefixed so a directory and a file can never collide. */
  id: string
  /** The backend uuid this node stands for. */
  refId: string
  kind: GraphNodeKind
  label: string
  path: string
  description: string | null
  fileCount: number
  directoryCount: number
  /** Child folders the depth-limited read did not return. */
  hiddenDirectories: number
  expandable: boolean
  expanded: boolean
  depth: number
  status?: string
  sizeBytes?: number
}

export interface GraphEdgeModel {
  id: string
  source: string
  target: string
}

export interface GraphModel {
  nodes: GraphNodeModel[]
  edges: GraphEdgeModel[]
  /** Every directory currently known, keyed by id (used to resolve search paths). */
  directories: Record<string, Directory>
}

export interface BuildGraphInput {
  root: Directory
  children: Record<string, Directory>
  expanded: Record<string, true>
  depth?: number
  /** Shown on the root card when the root directory has no name of its own. */
  rootLabel?: string
}

export const directoryNodeId = (directoryId: string): string => `dir:${directoryId}`
export const fileNodeId = (fileId: string): string => `file:${fileId}`

function fileNode(file: ProjectFile, depth: number): GraphNodeModel {
  return {
    id: fileNodeId(file.id),
    refId: file.id,
    kind: 'file',
    label: file.name,
    path: file.path,
    description: file.summary,
    fileCount: 0,
    directoryCount: 0,
    hiddenDirectories: 0,
    expandable: false,
    expanded: false,
    depth,
    status: file.summary_status,
    sizeBytes: file.size_bytes
  }
}

export function buildGraph({
  root,
  children,
  expanded,
  depth = TREE_DEPTH,
  rootLabel
}: BuildGraphInput): GraphModel {
  const nodes: GraphNodeModel[] = []
  const edges: GraphEdgeModel[] = []
  const directories: Record<string, Directory> = {}

  const visit = (directory: Directory): void => {
    directories[directory.id] = directory

    const fetched = children[directory.id]
    const childDirectories = fetched ? fetched.directories : directory.directories
    const files = fetched ? fetched.files : directory.files
    const complete = Boolean(fetched) || directory.depth + 1 < depth
    const isRoot = directory.depth === 0
    const isOpen = isRoot || Boolean(expanded[directory.id])
    const hiddenDirectories = complete
      ? 0
      : Math.max(0, directory.child_directory_count - childDirectories.length)

    const nodeId = directoryNodeId(directory.id)
    nodes.push({
      id: nodeId,
      refId: directory.id,
      kind: isRoot ? 'root' : 'folder',
      label: isRoot ? directory.name || rootLabel || 'Project root' : directory.name,
      path: directory.path,
      description: directory.description,
      fileCount: directory.direct_file_count,
      directoryCount: directory.child_directory_count,
      hiddenDirectories,
      expandable: !isRoot && (files.length > 0 || childDirectories.length > 0 || hiddenDirectories > 0),
      expanded: isOpen,
      depth: directory.depth
    })

    if (!isOpen) return

    for (const child of childDirectories) {
      edges.push({
        id: `${nodeId}->${directoryNodeId(child.id)}`,
        source: nodeId,
        target: directoryNodeId(child.id)
      })
      visit(child)
    }

    for (const file of files) {
      nodes.push(fileNode(file, directory.depth + 1))
      edges.push({ id: `${nodeId}->${fileNodeId(file.id)}`, source: nodeId, target: fileNodeId(file.id) })
    }
  }

  visit(root)
  return { nodes, edges, directories }
}

/** Every directory reachable from the tree plus the fetched subtrees. */
export function indexDirectories(
  root: Directory,
  children: Record<string, Directory>
): Map<string, Directory> {
  const index = new Map<string, Directory>()
  const queue: Directory[] = [root]

  while (queue.length > 0) {
    const current = queue.shift()
    if (!current || index.has(current.id)) continue
    index.set(current.id, current)
    const fetched = children[current.id]
    for (const child of fetched ? fetched.directories : current.directories) {
      if (!index.has(child.id)) queue.push(child)
    }
  }

  return index
}

/** Look a directory up by its human-readable path (what the search results return). */
export function directoryAtPath(
  root: Directory,
  children: Record<string, Directory>,
  path: string
): Directory | null {
  if (path === '') return root
  for (const directory of indexDirectories(root, children).values()) {
    if (directory.path === path) return directory
  }
  return null
}
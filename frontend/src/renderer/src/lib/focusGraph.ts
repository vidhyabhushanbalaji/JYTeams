/**
 * One view of the tree: a centre folder, its direct files, and its immediate subfolders.
 * Nothing deeper is ever in the model - pressing a folder is what moves you down, and the
 * API read behind each view is a single GET /directories/{id}.
 */

import type { Directory, ProjectFile } from '@shared/types'

export type FocusNodeKind = 'centre' | 'folder' | 'file'

export interface FocusNodeModel {
  /** React Flow id, prefixed so a directory and a file can never collide. */
  id: string
  /** The backend uuid this card stands for. */
  refId: string
  kind: FocusNodeKind
  label: string
  path: string
  description: string | null
  /** Direct files in this folder (0 for a file card). */
  fileCount: number
  /** Direct subfolders of this folder (0 for a file card). */
  directoryCount: number
  /** Folders are the way down; files are not. */
  navigable: boolean
  status?: string
  sizeBytes?: number
}

export interface FocusEdgeModel {
  id: string
  source: string
  target: string
}

export interface FocusViewModel {
  centre: FocusNodeModel
  files: FocusNodeModel[]
  folders: FocusNodeModel[]
  nodes: FocusNodeModel[]
  edges: FocusEdgeModel[]
}

export const directoryNodeId = (directoryId: string): string => `dir:${directoryId}`
export const fileNodeId = (fileId: string): string => `file:${fileId}`

const byName = (left: { name: string }, right: { name: string }): number =>
  left.name.localeCompare(right.name, undefined, { sensitivity: 'base' })

export interface BuildFocusInput {
  directory: Directory
  files: ProjectFile[]
  directories: Directory[]
  /** Used for the centre card when the root directory has no name of its own. */
  centreLabel?: string
}

export function buildFocusView({ directory, files, directories, centreLabel }: BuildFocusInput): FocusViewModel {
  const centre: FocusNodeModel = {
    id: directoryNodeId(directory.id),
    refId: directory.id,
    kind: 'centre',
    label: directory.name || centreLabel || 'Project root',
    path: directory.path,
    description: directory.description,
    fileCount: directory.direct_file_count,
    directoryCount: directory.child_directory_count,
    navigable: false
  }

  const fileNodes = [...files].sort(byName).map<FocusNodeModel>((file) => ({
    id: fileNodeId(file.id),
    refId: file.id,
    kind: 'file',
    label: file.name,
    path: file.path,
    description: file.summary,
    fileCount: 0,
    directoryCount: 0,
    navigable: false,
    status: file.summary_status,
    sizeBytes: file.size_bytes
  }))

  const folderNodes = [...directories].sort(byName).map<FocusNodeModel>((child) => ({
    id: directoryNodeId(child.id),
    refId: child.id,
    kind: 'folder',
    label: child.name,
    path: child.path,
    description: child.description,
    fileCount: child.direct_file_count,
    directoryCount: child.child_directory_count,
    navigable: true
  }))

  const edges: FocusEdgeModel[] = [...fileNodes, ...folderNodes].map((node) => ({
    id: `${centre.id}->${node.id}`,
    source: centre.id,
    target: node.id
  }))

  return { centre, files: fileNodes, folders: folderNodes, nodes: [centre, ...fileNodes, ...folderNodes], edges }
}
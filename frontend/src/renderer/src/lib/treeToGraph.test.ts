import { describe, expect, it } from 'vitest'

import type { Directory, ProjectFile } from '@shared/types'

import { buildGraph, directoryAtPath, indexDirectories, TREE_DEPTH } from './treeToGraph'

function file(id: string, name: string): ProjectFile {
  return {
    id,
    name,
    path: name,
    size_bytes: 12,
    summary: `summary of ${name}`,
    summary_status: 'ok',
    storage_bucket: null,
    storage_path: null
  }
}

function directory(input: Partial<Directory> & { id: string; name: string; depth: number }): Directory {
  return {
    path: input.name,
    description: `about ${input.name}`,
    direct_file_count: input.files?.length ?? 0,
    child_directory_count: input.directories?.length ?? 0,
    files: [],
    directories: [],
    ...input
  }
}

/**
 * The shape GET /projects/{id}/tree?depth=3 really returns: the root and two tiers of
 * folders, each with its files, and a level-2 folder whose own children were cut off.
 */
function fixture(): Directory {
  const api = directory({
    id: 'api',
    name: 'api',
    path: 'docs/api',
    depth: 2,
    files: [file('auth', 'auth.md')],
    child_directory_count: 1
  })
  const docs = directory({
    id: 'docs',
    name: 'docs',
    path: 'docs',
    depth: 1,
    files: [file('guide', 'guide.md')],
    directories: [api]
  })
  return directory({
    id: 'root',
    name: 'Docs project',
    path: '',
    depth: 0,
    files: [file('readme', 'README.md')],
    directories: [docs]
  })
}

describe('buildGraph', () => {
  it('draws the root and one tier of folders, with only the root\'s files', () => {
    const graph = buildGraph({ root: fixture(), children: {}, expanded: {} })

    expect(graph.nodes.map((node) => node.id)).toEqual(['dir:root', 'dir:docs', 'file:readme'])
    expect(graph.nodes.find((node) => node.id === 'dir:docs')?.expanded).toBe(false)
  })

  it('reveals an expanded folder\'s files and child folders', () => {
    const graph = buildGraph({ root: fixture(), children: {}, expanded: { docs: true } })

    expect(graph.nodes.map((node) => node.id)).toEqual([
      'dir:root',
      'dir:docs',
      'dir:api',
      'file:guide',
      'file:readme'
    ])
  })

  it('reports the folders a depth-limited read hid, so the chevron can offer them', () => {
    const graph = buildGraph({ root: fixture(), children: {}, expanded: { docs: true } })
    const api = graph.nodes.find((node) => node.id === 'dir:api')

    expect(api?.hiddenDirectories).toBe(1)
    expect(api?.expandable).toBe(true)
  })

  it('shows a truncated folder\'s files on expansion without another fetch', () => {
    const graph = buildGraph({ root: fixture(), children: {}, expanded: { docs: true, api: true } })

    expect(graph.nodes.map((node) => node.id)).toContain('file:auth')
  })

  it('prefers children fetched with GET /directories when they exist', () => {
    const fetched = directory({
      id: 'api',
      name: 'api',
      path: 'docs/api',
      depth: 2,
      files: [file('auth', 'auth.md')],
      directories: [directory({ id: 'tokens', name: 'tokens', path: 'docs/api/tokens', depth: 3 })]
    })

    const graph = buildGraph({
      root: fixture(),
      children: { api: fetched },
      expanded: { docs: true, api: true }
    })

    expect(graph.nodes.map((node) => node.id)).toContain('dir:tokens')
    expect(graph.nodes.find((node) => node.id === 'dir:api')?.hiddenDirectories).toBe(0)
  })

  it('never draws the root as expandable, because it is always open', () => {
    const graph = buildGraph({ root: fixture(), children: {}, expanded: {} })
    const root = graph.nodes.find((node) => node.id === 'dir:root')

    expect(root?.expandable).toBe(false)
    expect(root?.expanded).toBe(true)
  })

  it('falls back to the project name for a root directory that has no name', () => {
    const root = fixture()
    root.name = ''

    const graph = buildGraph({ root, children: {}, expanded: {}, rootLabel: 'Docs project' })

    expect(graph.nodes.find((node) => node.id === 'dir:root')?.label).toBe('Docs project')
  })

  it('agrees with the depth it is told to respect', () => {
    expect(TREE_DEPTH).toBe(3)
    const graph = buildGraph({ root: fixture(), children: {}, expanded: { docs: true, api: true } })
    const deepest = graph.nodes.filter((node) => node.kind !== 'file' && node.depth >= 3)
    expect(deepest).toHaveLength(0)
  })
})

describe('directory lookups', () => {
  it('indexes fetched subtrees as well as the depth-limited tree', () => {
    const fetched = directory({
      id: 'api',
      name: 'api',
      path: 'docs/api',
      depth: 2,
      directories: [directory({ id: 'tokens', name: 'tokens', path: 'docs/api/tokens', depth: 3 })]
    })

    const index = indexDirectories(fixture(), { api: fetched })
    expect(index.get('tokens')?.path).toBe('docs/api/tokens')
  })

  it('resolves the path a search hit reports', () => {
    const found = directoryAtPath(fixture(), {}, 'docs/api')
    expect(found?.id).toBe('api')
  })

  it('returns the root for the empty path', () => {
    expect(directoryAtPath(fixture(), {}, '')?.id).toBe('root')
  })

  it('returns null for a folder that is not loaded yet', () => {
    expect(directoryAtPath(fixture(), {}, 'docs/api/tokens')).toBeNull()
  })
})
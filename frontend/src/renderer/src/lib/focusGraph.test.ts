import { describe, expect, it } from 'vitest'

import type { Directory, ProjectFile } from '@shared/types'

import { buildFocusView, directoryNodeId, fileNodeId } from './focusGraph'

function file(id: string, name: string): ProjectFile {
  return {
    id,
    name,
    path: `docs/${name}`,
    size_bytes: 12,
    summary: `summary of ${name}`,
    summary_status: 'ok',
    storage_bucket: null,
    storage_path: null
  }
}

function directory(input: Partial<Directory> & { id: string; name: string }): Directory {
  return {
    path: input.name,
    depth: 1,
    description: `about ${input.name}`,
    direct_file_count: input.files?.length ?? 0,
    child_directory_count: input.directories?.length ?? 0,
    files: [],
    directories: [],
    ...input
  }
}

describe('buildFocusView', () => {
  const grandchild = directory({ id: 'tokens', name: 'tokens', path: 'docs/api/tokens' })
  const child = directory({
    id: 'api',
    name: 'api',
    path: 'docs/api',
    files: [file('auth', 'auth.md')],
    directories: [grandchild]
  })

  it('draws the centre, its direct files and its immediate folders only', () => {
    const view = buildFocusView({
      directory: directory({ id: 'docs', name: 'docs', path: 'docs', depth: 1 }),
      files: [file('arch', 'architecture.md')],
      directories: [child]
    })

    expect(view.nodes.map((node) => node.id)).toEqual(['dir:docs', 'file:arch', 'dir:api'])
    expect(view.nodes.map((node) => node.id)).not.toContain('file:auth')
    expect(view.nodes.map((node) => node.id)).not.toContain('dir:tokens')
  })

  it('marks folders as the way down and files as a dead end', () => {
    const view = buildFocusView({
      directory: directory({ id: 'docs', name: 'docs' }),
      files: [file('arch', 'architecture.md')],
      directories: [child]
    })

    expect(view.centre.navigable).toBe(false)
    expect(view.folders.every((node) => node.navigable)).toBe(true)
    expect(view.files.every((node) => !node.navigable)).toBe(true)
  })

  it('sorts both rings by name so the wheel is stable', () => {
    const view = buildFocusView({
      directory: directory({ id: 'docs', name: 'docs' }),
      files: [file('b', 'beta.md'), file('a', 'Alpha.md')],
      directories: [directory({ id: 'z', name: 'guides' }), directory({ id: 'y', name: 'api' })]
    })

    expect(view.files.map((node) => node.label)).toEqual(['Alpha.md', 'beta.md'])
    expect(view.folders.map((node) => node.label)).toEqual(['api', 'guides'])
  })

  it('spokes every child off the centre', () => {
    const view = buildFocusView({
      directory: directory({ id: 'docs', name: 'docs' }),
      files: [file('a', 'a.md')],
      directories: [child]
    })

    expect(view.edges).toEqual([
      { id: `${directoryNodeId('docs')}->${fileNodeId('a')}`, source: directoryNodeId('docs'), target: fileNodeId('a') },
      { id: `${directoryNodeId('docs')}->${directoryNodeId('api')}`, source: directoryNodeId('docs'), target: directoryNodeId('api') }
    ])
  })

  it('falls back to the project name for a nameless root', () => {
    const view = buildFocusView({
      directory: directory({ id: 'root', name: '', path: '', depth: 0 }),
      files: [],
      directories: [],
      centreLabel: 'Docs-flat'
    })

    expect(view.centre.label).toBe('Docs-flat')
    expect(view.nodes).toHaveLength(1)
    expect(view.edges).toEqual([])
  })
})
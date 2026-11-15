import { describe, expect, it } from 'vitest'

import { MAX_FILE_NAME, draftFileName, draftSizeBytes } from './documentDraft'

// The rules mirror backend/app/graph_add/labels.py (`validate_file_name`), so a name this
// module accepts must survive the round trip to `POST /api/graph-add/suggestions`.
describe('draftFileName', () => {
  it('adds a markdown suffix when none was typed', () => {
    expect(draftFileName('release checklist')).toEqual({
      name: 'release checklist.md',
      error: null
    })
  })

  it('keeps an existing markdown suffix and normalises its case', () => {
    expect(draftFileName('runbook.MD').name).toBe('runbook.md')
    expect(draftFileName('notes.markdown').name).toBe('notes.markdown')
    expect(draftFileName('page.mdx').name).toBe('page.mdx')
  })

  it('trims whitespace and normalises unicode', () => {
    expect(draftFileName('  Cafe\u0301 notes  ').name).toBe('Caf\u00e9 notes.md')
  })

  it('drops a trailing dot instead of doubling it', () => {
    expect(draftFileName('Notes.').name).toBe('Notes.md')
  })

  it('rejects an empty or suffix-only name', () => {
    expect(draftFileName('').error).toBe('a file name is required')
    expect(draftFileName('   ').error).toBe('a file name is required')
    expect(draftFileName('.md').error).toBe('a file name is required')
  })

  it('rejects separators and dot names', () => {
    expect(draftFileName('a/b.md').error).toBe('a file name cannot contain a slash')
    expect(draftFileName('a\\b.md').error).toBe('a file name cannot contain a slash')
    expect(draftFileName('..').error).toContain('not a usable file name')
  })

  it('caps the final name at the backend limit', () => {
    const long = draftFileName(`${'a'.repeat(MAX_FILE_NAME)}.md`)
    expect(long.error).toBe(`file names are limited to ${MAX_FILE_NAME} characters`)
    expect(draftFileName('a'.repeat(MAX_FILE_NAME - 3)).error).toBeNull()
  })
})

describe('draftSizeBytes', () => {
  it('counts UTF-8 bytes, as the backend does', () => {
    expect(draftSizeBytes('')).toBe(0)
    expect(draftSizeBytes('plan')).toBe(4)
    expect(draftSizeBytes('\u00e9')).toBe(2)
    expect(draftSizeBytes('# Caf\u00e9\n')).toBe(8)
  })
})

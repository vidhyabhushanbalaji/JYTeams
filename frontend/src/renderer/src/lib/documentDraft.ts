/**
 * Naming a document that does not exist yet.
 *
 * A document written in the app is posted to the same Graph Add endpoint an upload uses, so its
 * name has to satisfy the backend's `validate_file_name` rules: markdown, no separators, at most
 * 120 characters. Checking here answers a typo in the form instead of after a round trip; the
 * backend stays the authority, so its message still wins if the two ever disagree.
 */

const MARKDOWN_SUFFIXES = ['.md', '.markdown', '.mdx'] as const

/** Mirrors `backend/app/graph_add/labels.py` (`MAX_FILE_NAME`). */
export const MAX_FILE_NAME = 120

/** Starting point for a new document's body, shown in the empty editor. */
export const DRAFT_PLACEHOLDER = `# Title

Start writing. The document is rendered beside the editor, and it joins the graph once you choose a folder.`

export interface DraftName {
  /** The name to send, with a markdown suffix (empty when nothing was typed). */
  name: string
  /** Why the name cannot be used, or `null` when it can. */
  error: string | null
}

/** Clean a typed file name: trim, NFC, append `.md`, and explain anything unusable. */
export function draftFileName(raw: string): DraftName {
  const trimmed = (raw ?? '').normalize('NFC').trim()
  if (!trimmed) return { name: '', error: 'a file name is required' }
  if (trimmed === '.' || trimmed === '..') {
    return { name: trimmed, error: `${trimmed} is not a usable file name` }
  }
  if (trimmed.includes('/') || trimmed.includes('\\')) {
    return { name: trimmed, error: 'a file name cannot contain a slash' }
  }
  if (trimmed.includes('\u0000')) {
    return { name: trimmed, error: 'invalid character in file name' }
  }

  const suffix = MARKDOWN_SUFFIXES.find((item) => trimmed.toLowerCase().endsWith(item))
  // `Notes.` would otherwise become `Notes..md`; a trailing dot is not part of a name.
  const stem = (suffix ? trimmed.slice(0, -suffix.length) : trimmed).replace(/[.\s]+$/, '')
  if (!stem) return { name: trimmed, error: 'a file name is required' }

  const name = `${stem}${suffix ?? '.md'}`
  if (name.length > MAX_FILE_NAME) {
    return { name, error: `file names are limited to ${MAX_FILE_NAME} characters` }
  }
  return { name, error: null }
}

/** The document's size in bytes, as the backend will count it (UTF-8). */
export function draftSizeBytes(text: string): number {
  return new TextEncoder().encode(text).length
}

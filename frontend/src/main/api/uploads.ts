/**
 * The write side: a whole folder becomes a new project, and one document is offered a home.
 *
 * Uploads are assembled here from disk. The backend reads the relative path out of each
 * multipart part's filename (`docs/api/auth.md`), which is exactly what the folder walk
 * produces, so no zip step is needed.
 */

import { readFile, stat } from 'node:fs/promises'
import { basename } from 'node:path'

import type {
  DraftSuggestionInput,
  PickedFile,
  PlacementInput,
  PlacementResult,
  SuggestionAccepted,
  UploadAccepted
} from '../../shared/types'
import { collectMarkdownFiles, previewFolder } from '../fs/walk'
import { LONG_TIMEOUT_MS, request } from './client'

export const inspectFolder = previewFolder

export async function uploadFolder(input: { name: string; folderPath: string }): Promise<UploadAccepted> {
  const files = await collectMarkdownFiles(input.folderPath)
  if (files.length === 0) {
    throw new Error('That folder has no markdown files. Add .md, .markdown or .mdx files and try again.')
  }

  const form = new FormData()
  form.append('mode', 'new')
  form.append('name', input.name)
  for (const file of files) {
    const bytes = await readFile(file.absolutePath)
    form.append('files', new File([bytes], file.relativePath, { type: 'text/markdown' }))
  }

  return request<UploadAccepted>('/api/graph-creation/uploads', {
    method: 'POST',
    body: form,
    timeoutMs: LONG_TIMEOUT_MS
  })
}

export async function inspectFile(filePath: string): Promise<PickedFile> {
  const info = await stat(filePath)
  return { path: filePath, name: basename(filePath), sizeBytes: info.size }
}

export async function suggestPlacement(input: {
  projectId: string
  filePath: string
  context?: string
}): Promise<SuggestionAccepted> {
  const bytes = await readFile(input.filePath)
  if (bytes.length === 0) throw new Error('That file is empty.')

  const form = new FormData()
  form.append('project_id', input.projectId)
  if (input.context) form.append('context', input.context)
  form.append('file', new File([bytes], basename(input.filePath), { type: 'text/markdown' }))

  return request<SuggestionAccepted>('/api/graph-add/suggestions', {
    method: 'POST',
    body: form,
    timeoutMs: LONG_TIMEOUT_MS
  })
}

/**
 * Rank the folders for a document written in the app.
 *
 * Nothing touches the disk: the editor's text becomes the bytes of the same multipart part an
 * upload would carry, so Graph Add stores and scores it exactly as if it had been read from a
 * file. Scored locally in the backend - no model call.
 */
export async function suggestDraftPlacement(input: DraftSuggestionInput): Promise<SuggestionAccepted> {
  const bytes = new TextEncoder().encode(input.text)
  if (bytes.length === 0) {
    throw new Error('The document is empty. Write something before finding it a folder.')
  }

  const form = new FormData()
  form.append('project_id', input.projectId)
  if (input.context) form.append('context', input.context)
  form.append('file', new File([bytes], input.fileName, { type: 'text/markdown' }))

  return request<SuggestionAccepted>('/api/graph-add/suggestions', {
    method: 'POST',
    body: form,
    timeoutMs: LONG_TIMEOUT_MS
  })
}

export async function placeFile(input: PlacementInput): Promise<PlacementResult> {
  return request<PlacementResult>('/api/graph-add/placements', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
    timeoutMs: LONG_TIMEOUT_MS
  })
}
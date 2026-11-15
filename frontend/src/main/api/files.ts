/** One document's body: read it for the viewer, write it back after an edit.
 *
 * Saving never rewrites the old blob — the backend stores the new text under its own digest
 * and repoints the file row — and it makes no model call, so folder descriptions refresh on
 * the next add or placement rather than here.
 */

import type { FileContent, FileSaved } from '../../shared/types'
import { request } from './client'

const CREATION = '/api/graph-creation'

const id = encodeURIComponent

export const readFileContent = (fileId: string): Promise<FileContent> =>
  request(`${CREATION}/files/${id(fileId)}/content`)

export const saveFileContent = (
  fileId: string,
  input: { text: string; expectedSha256?: string | null }
): Promise<FileSaved> =>
  request(`${CREATION}/files/${id(fileId)}/content`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: input.text,
      expected_sha256: input.expectedSha256 ?? null
    })
  })

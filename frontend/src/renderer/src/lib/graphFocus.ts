/**
 * What another screen asks the project graph to show: a set of documents (a ticket's files, a
 * chat message's mentions) or one folder (a chat mention of a directory).
 *
 * Both carry the path the graph must reveal first, because the graph draws one folder at a time.
 */

import type { ChatMention } from '@shared/types'

export interface FocusFileTarget {
  fileId: string
  directoryPath: string
  name: string
}

export type GraphFocus =
  | {
      kind: 'files'
      /** A human label for the strip above the canvas, e.g. "#12 Fix the login redirect". */
      label: string
      targets: FocusFileTarget[]
      /** The file the graph should reveal and focus; the rest stay highlighted. */
      entryFileId: string
    }
  | {
      kind: 'directory'
      label: string
      directoryId: string
      directoryPath: string
    }

/** A ticket hands the graph files; the shape the tickets screen already builds. */
export type TicketFocus = Extract<GraphFocus, { kind: 'files' }>
export type TicketFocusTarget = FocusFileTarget

export const focusForFile = (
  focus: TicketFocus,
  fileId: string
): FocusFileTarget | null => focus.targets.find((target) => target.fileId === fileId) ?? null

/**
 * What pressing a chat mention should open. A ticket has no graph target (it opens the tickets
 * screen instead), so it answers `null`.
 */
export function focusFromMention(mention: ChatMention): GraphFocus | null {
  if (mention.kind === 'file') {
    return {
      kind: 'files',
      label: mention.label,
      targets: [
        {
          fileId: mention.id,
          directoryPath: mention.directory_path,
          name: mention.label
        }
      ],
      entryFileId: mention.id
    }
  }
  if (mention.kind === 'directory') {
    return {
      kind: 'directory',
      label: mention.label,
      directoryId: mention.id,
      directoryPath: mention.path
    }
  }
  return null
}

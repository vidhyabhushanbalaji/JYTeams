/** What a ticket hands the graph: which files to highlight, and which one to open first. */

export interface TicketFocusTarget {
  fileId: string
  directoryPath: string
  name: string
}

export interface TicketFocus {
  /** A human label for the strip above the canvas, e.g. "#12 Fix the login redirect". */
  label: string
  targets: TicketFocusTarget[]
  /** The file the graph should reveal and focus; the rest stay highlighted. */
  entryFileId: string
}

export const focusForFile = (
  focus: TicketFocus,
  fileId: string
): TicketFocusTarget | null => focus.targets.find((target) => target.fileId === fileId) ?? null

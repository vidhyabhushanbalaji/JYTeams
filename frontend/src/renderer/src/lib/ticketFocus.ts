/**
 * The graph focus model now lives in `graphFocus.ts` (it covers folders as well as files).
 * This module remains the import site the tickets screen uses.
 */

export type { TicketFocus, TicketFocusTarget } from './graphFocus'
export { focusForFile } from './graphFocus'

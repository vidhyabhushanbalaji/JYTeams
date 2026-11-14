/**
 * The project tree: the centre folder at the top, its files on short branches close to it,
 * its immediate subfolders much further down on long branches.
 *
 * A single trunk runs down x = 0 and every card hangs off it. **No card is ever placed on
 * the trunk**, which is what lets a folder branch travel past the whole file band without
 * crossing a card - the geometry does the routing, no special cases.
 *
 * Children wrap into more rows rather than one wide row, so a folder with many files grows
 * downwards (taller, easier to read) instead of sideways.
 */

import type { XYPosition } from '@shared/types'

export interface CardSize {
  width: number
  height: number
}

/** Kept in step with .node--centre / .node--file / .node--folder in app.css. */
export const CENTRE_SIZE: CardSize = { width: 264, height: 136 }
export const FILE_SIZE: CardSize = { width: 240, height: 110 }
export const FOLDER_SIZE: CardSize = { width: 240, height: 124 }

/** Gap between a card top and the horizontal rail its branch runs along. */
export const RAIL_GAP = 24

/** Inner pair first, so a row of one or two stays balanced around the trunk. */
const COLUMN_OFFSETS = [-150, 150, -414, 414]
const ROW_GAP = 64
const BAND_GAP = 120
const FIRST_ROW_TOP = CENTRE_SIZE.height + 104

const rowsFor = (count: number): number => Math.ceil(count / COLUMN_OFFSETS.length)

function placeBand(count: number, size: CardSize, rowTop: (row: number) => number): XYPosition[] {
  const positions: XYPosition[] = []
  for (let index = 0; index < count; index += 1) {
    const row = Math.floor(index / COLUMN_OFFSETS.length)
    const column = index % COLUMN_OFFSETS.length
    positions.push({ x: COLUMN_OFFSETS[column] - size.width / 2, y: rowTop(row) })
  }
  return positions
}

export interface TreeLayout {
  centre: XYPosition
  files: XYPosition[]
  folders: XYPosition[]
  /** Top of the file band and of the folder band, for tests and debugging. */
  bands: { files: number; folders: number }
}

export function layoutTree(counts: { files: number; folders: number }): TreeLayout {
  const centre: XYPosition = { x: -CENTRE_SIZE.width / 2, y: -CENTRE_SIZE.height / 2 }

  const fileRows = rowsFor(counts.files)
  const fileTop = (row: number): number => FIRST_ROW_TOP + row * (FILE_SIZE.height + ROW_GAP)
  const files = placeBand(counts.files, FILE_SIZE, fileTop)

  // Folders hang past the whole file band; with no files they take the first row instead.
  const folderTop = fileRows > 0 ? fileTop(fileRows - 1) + FILE_SIZE.height + BAND_GAP : FIRST_ROW_TOP
  const folders = placeBand(
    counts.folders,
    FOLDER_SIZE,
    (row) => folderTop + row * (FOLDER_SIZE.height + ROW_GAP)
  )

  return { centre, files, folders, bands: { files: FIRST_ROW_TOP, folders: folderTop } }
}

interface TreeMember {
  id: string
}

/** Positions keyed by React Flow node id, ready to merge under the user drags. */
export function treePositions(view: {
  centre: TreeMember
  files: TreeMember[]
  folders: TreeMember[]
}): Record<string, XYPosition> {
  const layout = layoutTree({ files: view.files.length, folders: view.folders.length })
  const positions: Record<string, XYPosition> = { [view.centre.id]: layout.centre }
  view.files.forEach((node, index) => {
    positions[node.id] = layout.files[index]
  })
  view.folders.forEach((node, index) => {
    positions[node.id] = layout.folders[index]
  })
  return positions
}
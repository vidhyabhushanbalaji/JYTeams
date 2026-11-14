/**
 * The project tree: the centre folder at the top, its files on short branches close to it,
 * its immediate subfolders much further down on long branches.
 *
 * The layout is organic but not random. Every card gets a small offset derived from a hash of
 * its id, so the tree looks hand-placed while staying identical across renders, sessions and
 * machines - a layout that moved on its own would undo the drag and flicker work. The jitter
 * budget is chosen so cards still cannot touch; `treeLayout.test.ts` asserts that over
 * hundreds of id sets.
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

/** Inner pair first, so a row of one or two stays balanced around the stem. */
export const COLUMNS = [-174, 174, -474, 474] as const

const ROW_GAP = 84
const BAND_GAP = 120
const FIRST_ROW_TOP = CENTRE_SIZE.height + 104

/** Bounded wander per card: small enough that the minimum gaps stay positive. */
export const JITTER = { x: 26, y: 22 } as const

/** FNV-1a: tiny, deterministic, and identical everywhere. */
export function hashSeed(text: string): number {
  let value = 2166136261
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index)
    value = Math.imul(value, 16777619)
  }
  return value >>> 0
}

/** A deterministic value in [-amount, amount] for one seed and salt pair. */
export function seededOffset(seed: string, salt: string, amount: number): number {
  const value = hashSeed(`${seed}|${salt}`)
  return ((value % 2001) / 1000 - 1) * amount
}

export interface TreeMember {
  id: string
}

const round = (value: number): number => Math.round(value)

function placeBand(
  members: TreeMember[],
  size: CardSize,
  rowTop: (row: number) => number
): XYPosition[] {
  return members.map((member, index) => {
    const row = Math.floor(index / COLUMNS.length)
    const column = index % COLUMNS.length
    return {
      x: round(COLUMNS[column] - size.width / 2 + seededOffset(member.id, 'x', JITTER.x)),
      y: round(rowTop(row) + seededOffset(member.id, 'y', JITTER.y))
    }
  })
}

export interface TreeLayout {
  centre: XYPosition
  files: XYPosition[]
  folders: XYPosition[]
  bands: { files: number; folders: number }
}

export function layoutTree(input: { files: TreeMember[]; folders: TreeMember[] }): TreeLayout {
  const centre: XYPosition = { x: -CENTRE_SIZE.width / 2, y: -CENTRE_SIZE.height / 2 }

  const fileRows = Math.ceil(input.files.length / COLUMNS.length)
  const fileTop = (row: number): number => FIRST_ROW_TOP + row * (FILE_SIZE.height + ROW_GAP)
  const files = placeBand(input.files, FILE_SIZE, fileTop)

  // Folders hang past the whole file band; with no files they take the first row instead.
  const folderTop =
    fileRows > 0 ? fileTop(fileRows - 1) + FILE_SIZE.height + BAND_GAP : FIRST_ROW_TOP
  const folders = placeBand(input.folders, FOLDER_SIZE, (row) =>
    folderTop + row * (FOLDER_SIZE.height + ROW_GAP)
  )

  return { centre, files, folders, bands: { files: FIRST_ROW_TOP, folders: folderTop } }
}

/** Positions keyed by React Flow node id, ready to merge under the user drags. */
export function treePositions(view: {
  centre: TreeMember
  files: TreeMember[]
  folders: TreeMember[]
}): Record<string, XYPosition> {
  const layout = layoutTree({ files: view.files, folders: view.folders })
  const positions: Record<string, XYPosition> = { [view.centre.id]: layout.centre }
  view.files.forEach((node, index) => {
    positions[node.id] = layout.files[index]
  })
  view.folders.forEach((node, index) => {
    positions[node.id] = layout.folders[index]
  })
  return positions
}
import { describe, expect, it } from 'vitest'

import {
  CENTRE_SIZE,
  COLUMNS,
  FILE_SIZE,
  FOLDER_SIZE,
  JITTER,
  layoutTree,
  seededOffset,
  treePositions,
  type TreeLayout,
  type TreeMember
} from './treeLayout'

interface Rect {
  id: string
  x: number
  y: number
  w: number
  h: number
}

function ids(prefix: string, count: number): TreeMember[] {
  return Array.from({ length: count }, (_, index) => ({ id: `${prefix}-${index}` }))
}

function rects(layout: TreeLayout): Rect[] {
  const list: Rect[] = [
    { id: 'centre', x: layout.centre.x, y: layout.centre.y, w: CENTRE_SIZE.width, h: CENTRE_SIZE.height }
  ]
  layout.files.forEach((point, index) => {
    list.push({ id: `file-${index}`, x: point.x, y: point.y, w: FILE_SIZE.width, h: FILE_SIZE.height })
  })
  layout.folders.forEach((point, index) => {
    list.push({
      id: `folder-${index}`,
      x: point.x,
      y: point.y,
      w: FOLDER_SIZE.width,
      h: FOLDER_SIZE.height
    })
  })
  return list
}

function overlaps(left: Rect, right: Rect): boolean {
  return (
    left.x < right.x + right.w &&
    left.x + left.w > right.x &&
    left.y < right.y + right.h &&
    left.y + left.h > right.y
  )
}

function collisions(layout: TreeLayout): string[] {
  const list = rects(layout)
  const found: string[] = []
  for (let i = 0; i < list.length; i += 1) {
    for (let j = i + 1; j < list.length; j += 1) {
      if (overlaps(list[i], list[j])) found.push(`${list[i].id} x ${list[j].id}`)
    }
  }
  return found
}

const lowest = (points: Array<{ y: number }>): number => Math.max(...points.map((point) => point.y))

describe('layoutTree', () => {
  it('puts the centre card at the origin, at the top', () => {
    const layout = layoutTree({ files: ids('f', 2), folders: ids('d', 2) })
    expect(layout.centre).toEqual({ x: -CENTRE_SIZE.width / 2, y: -CENTRE_SIZE.height / 2 })
  })

  it('never places two cards on top of each other, whatever the ids', () => {
    // 300 different id sets: the jitter is seeded from the id, so this walks the whole space.
    for (let run = 0; run < 300; run += 1) {
      const layout = layoutTree({
        files: ids(`run-${run}-file`, run % 13),
        folders: ids(`run-${run}-folder`, (run * 7) % 9)
      })
      const found = collisions(layout)
      expect(found, `run ${run}: ${found.join(', ')}`).toEqual([])
    }
  })

  it('keeps every child strictly below the centre card', () => {
    const layout = layoutTree({ files: ids('f', 7), folders: ids('d', 5) })
    const centreBottom = layout.centre.y + CENTRE_SIZE.height

    for (const point of [...layout.files, ...layout.folders]) {
      expect(point.y).toBeGreaterThan(centreBottom)
    }
  })

  it('keeps the stem at x = 0 clear of every child', () => {
    const layout = layoutTree({ files: ids('f', 8), folders: ids('d', 6) })
    const children = rects(layout).filter((rect) => rect.id !== 'centre')

    for (const rect of children) {
      expect(rect.x + rect.w <= 0 || rect.x >= 0, rect.id).toBe(true)
    }
  })

  it('puts the whole file band above the folder band', () => {
    const layout = layoutTree({ files: ids('f', 6), folders: ids('d', 4) })
    const lowestFile = lowest(layout.files.map((point) => ({ y: point.y + FILE_SIZE.height })))
    const highestFolder = Math.min(...layout.folders.map((point) => point.y))

    expect(highestFolder).toBeGreaterThan(lowestFile)
  })

  it('grows downwards rather than sideways when a band fills up', () => {
    const two = layoutTree({ files: ids('f', 2), folders: [] })
    const six = layoutTree({ files: ids('f', 6), folders: [] })

    expect(lowest(six.files)).toBeGreaterThan(lowest(two.files))
    expect(six.files).toHaveLength(6)
  })

  it('keeps every card inside its jitter budget', () => {
    const layout = layoutTree({ files: ids('f', 8), folders: ids('d', 5) })

    layout.files.forEach((point, index) => {
      const base = COLUMNS[index % COLUMNS.length]
      const drifted = Math.abs(point.x + FILE_SIZE.width / 2 - base)
      expect(drifted).toBeLessThanOrEqual(JITTER.x + 0.5)
    })
  })

  it('is deterministic, and different ids land in different places', () => {
    const first = layoutTree({ files: ids('a', 4), folders: ids('b', 3) })
    const again = layoutTree({ files: ids('a', 4), folders: ids('b', 3) })
    const other = layoutTree({ files: ids('c', 4), folders: ids('d', 3) })

    expect(first).toEqual(again)
    expect(first.files).not.toEqual(other.files)
  })

  it('draws nothing for an empty folder', () => {
    const empty = layoutTree({ files: [], folders: [] })
    expect(empty.files).toEqual([])
    expect(empty.folders).toEqual([])
  })
})

describe('seededOffset', () => {
  it('stays inside the requested range and repeats for the same seed', () => {
    for (let index = 0; index < 200; index += 1) {
      const value = seededOffset(`id-${index}`, 'x', 26)
      expect(Math.abs(value)).toBeLessThanOrEqual(26)
      expect(seededOffset(`id-${index}`, 'x', 26)).toBe(value)
    }
  })
})

describe('treePositions', () => {
  it('keys every position by node id', () => {
    const positions = treePositions({
      centre: { id: 'dir:root' },
      files: [{ id: 'file:a' }, { id: 'file:b' }],
      folders: [{ id: 'dir:docs' }]
    })

    expect(Object.keys(positions).sort()).toEqual(['dir:docs', 'dir:root', 'file:a', 'file:b'])
  })
})
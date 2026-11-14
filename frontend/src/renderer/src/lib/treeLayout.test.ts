import { describe, expect, it } from 'vitest'

import {
  CENTRE_SIZE,
  FILE_SIZE,
  FOLDER_SIZE,
  layoutTree,
  treePositions,
  type TreeLayout
} from './treeLayout'

interface Rect {
  id: string
  x: number
  y: number
  w: number
  h: number
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
    const layout = layoutTree({ files: 2, folders: 2 })
    expect(layout.centre).toEqual({ x: -CENTRE_SIZE.width / 2, y: -CENTRE_SIZE.height / 2 })
  })

  it('never places two cards on top of each other', () => {
    const cases = [
      { files: 0, folders: 0 },
      { files: 1, folders: 0 },
      { files: 0, folders: 1 },
      { files: 1, folders: 1 },
      { files: 2, folders: 2 },
      { files: 3, folders: 0 },
      { files: 4, folders: 4 },
      { files: 5, folders: 3 },
      { files: 9, folders: 6 },
      { files: 12, folders: 25 },
      { files: 25, folders: 40 }
    ]

    for (const counts of cases) {
      const found = collisions(layoutTree(counts))
      expect(found, `${counts.files} files / ${counts.folders} folders`).toEqual([])
    }
  })

  it('keeps every child strictly below the centre card', () => {
    const layout = layoutTree({ files: 7, folders: 5 })
    const centreBottom = layout.centre.y + CENTRE_SIZE.height

    for (const point of [...layout.files, ...layout.folders]) {
      expect(point.y).toBeGreaterThan(centreBottom)
    }
  })

  it('keeps the trunk at x = 0 clear of every card', () => {
    const layout = layoutTree({ files: 8, folders: 6 })

    // The centre card sits on the trunk by definition; its children must not.
    for (const rect of rects(layout).filter((item) => item.id !== 'centre')) {
      expect(rect.x + rect.w <= 0 || rect.x >= 0, rect.id).toBe(true)
    }
  })

  it('puts the whole file band above the folder band', () => {
    const layout = layoutTree({ files: 6, folders: 4 })
    const lowestFile = lowest(layout.files.map((point) => ({ y: point.y + FILE_SIZE.height })))
    const highestFolder = Math.min(...layout.folders.map((point) => point.y))

    expect(highestFolder).toBeGreaterThan(lowestFile)
  })

  it('grows downwards rather than sideways when a band fills up', () => {
    const two = layoutTree({ files: 2, folders: 0 })
    const six = layoutTree({ files: 6, folders: 0 })

    expect(lowest(six.files)).toBeGreaterThan(lowest(two.files))
    expect(six.files).toHaveLength(6)
  })

  it('mirrors a full row around the trunk', () => {
    const layout = layoutTree({ files: 4, folders: 0 })
    const centres = layout.files
      .map((point) => point.x + FILE_SIZE.width / 2)
      .sort((left, right) => left - right)

    expect(centres).toEqual([-414, -150, 150, 414])
  })

  it('is deterministic and draws nothing for an empty folder', () => {
    expect(layoutTree({ files: 3, folders: 2 })).toEqual(layoutTree({ files: 3, folders: 2 }))

    const empty = layoutTree({ files: 0, folders: 0 })
    expect(empty.files).toEqual([])
    expect(empty.folders).toEqual([])
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
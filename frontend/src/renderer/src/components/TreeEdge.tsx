/**
 * A branch: a cubic curve from the centre card's underside to the top of one child.
 *
 * The control points turn late, so a long branch (a folder) first drops close to the stem,
 * passes the file band through the clear middle channel, and only then swings out to its
 * card - which is what makes it read as a branch instead of a wire. The small seeded sway and
 * the 1.0-1.4 px stroke give each branch its own weight, so no two look stamped.
 *
 * Geometry comes from the live nodes, so dragging a card keeps its branch attached.
 */

import { BaseEdge, useInternalNode, type EdgeProps } from '@xyflow/react'

import { seededOffset } from '../lib/treeLayout'

const trim = (value: number): number => Math.round(value * 10) / 10

export function TreeEdge({ id, source, target }: EdgeProps) {
  const from = useInternalNode(source)
  const to = useInternalNode(target)

  if (!from || !to) return null

  const sourceX = from.internals.positionAbsolute.x + (from.measured?.width ?? 0) / 2
  const sourceY = from.internals.positionAbsolute.y + (from.measured?.height ?? 0)
  const targetX = to.internals.positionAbsolute.x + (to.measured?.width ?? 0) / 2
  const targetY = to.internals.positionAbsolute.y

  const span = Math.max(40, targetY - sourceY)
  const sway = seededOffset(id, 'sway', 18)
  const weight = trim(1 + (seededOffset(id, 'weight', 0.5) + 0.5) * 0.4)

  const control1X = trim(sourceX + sway * 0.65)
  const control1Y = trim(sourceY + span * 0.52)
  const control2X = trim(targetX + sway)
  const control2Y = trim(targetY - span * 0.24)

  const path = `M ${trim(sourceX)} ${trim(sourceY)} C ${control1X} ${control1Y}, ${control2X} ${control2Y}, ${trim(targetX)} ${trim(targetY)}`

  return <BaseEdge id={id} path={path} style={{ strokeWidth: weight }} />
}
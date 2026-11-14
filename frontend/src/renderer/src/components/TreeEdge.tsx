/**
 * A branch: down the trunk, across the rail just above the child row, then into the card.
 *
 * Every edge draws its own trunk segment from the centre card, and they overlap exactly, so
 * the tree reads as one continuous trunk. Short branches (files) turn almost immediately;
 * long ones (folders) travel the whole way down first, which is the point of the shape.
 *
 * Positions come from the live nodes, so dragging a card keeps its branch attached.
 */

import { BaseEdge, useInternalNode, type EdgeProps } from '@xyflow/react'

import { RAIL_GAP } from '../lib/treeLayout'

export function TreeEdge({ id, source, target }: EdgeProps) {
  const from = useInternalNode(source)
  const to = useInternalNode(target)

  if (!from || !to) return null

  const sourceX = from.internals.positionAbsolute.x + (from.measured?.width ?? 0) / 2
  const sourceY = from.internals.positionAbsolute.y + (from.measured?.height ?? 0)
  const targetX = to.internals.positionAbsolute.x + (to.measured?.width ?? 0) / 2
  const targetY = to.internals.positionAbsolute.y

  // Never turn back above the centre card, even if a card is dragged upwards.
  const railY = Math.max(sourceY + 16, targetY - RAIL_GAP)

  const path = `M ${sourceX} ${sourceY} L ${sourceX} ${railY} L ${targetX} ${railY} L ${targetX} ${targetY}`
  return <BaseEdge id={id} path={path} />
}
/**
 * A tidy left-to-right tree, computed with dagre over the visible nodes only.
 *
 * Everything the user dragged keeps the position they gave it: the layout is merged under
 * the stored positions by the caller, so a re-layout never undoes a deliberate move.
 */

import * as dagre from '@dagrejs/dagre'

import type { GraphEdgeModel, GraphNodeKind, GraphNodeModel } from './treeToGraph'

export interface Size {
  width: number
  height: number
}

/** Kept in step with .node / .node--root in app.css. */
export const NODE_SIZE: Record<GraphNodeKind, Size> = {
  root: { width: 264, height: 136 },
  folder: { width: 240, height: 124 },
  file: { width: 240, height: 110 }
}

export type Positions = Record<string, { x: number; y: number }>

export function layoutModel(nodes: GraphNodeModel[], edges: GraphEdgeModel[]): Positions {
  if (nodes.length === 0) return {}

  const graph = new dagre.graphlib.Graph()
  graph.setGraph({ rankdir: 'LR', nodesep: 16, ranksep: 92, marginx: 24, marginy: 24 })
  graph.setDefaultEdgeLabel(() => ({}) as Record<string, unknown>)

  for (const node of nodes) {
    graph.setNode(node.id, NODE_SIZE[node.kind])
  }
  for (const edge of edges) {
    graph.setEdge(edge.source, edge.target)
  }

  dagre.layout(graph)

  const positions: Positions = {}
  for (const node of nodes) {
    const laidOut = graph.node(node.id) as { x: number; y: number; width: number; height: number } | undefined
    if (!laidOut) continue
    positions[node.id] = {
      x: Math.round(laidOut.x - laidOut.width / 2),
      y: Math.round(laidOut.y - laidOut.height / 2)
    }
  }
  return positions
}
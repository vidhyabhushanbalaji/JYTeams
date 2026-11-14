/**
 * The canvas. Positions come from the graph hook (layout merged under the user\'s drags);
 * React Flow\'s own position changes are held locally only while a drag is in flight, so a
 * node never springs back before it is persisted.
 */

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type NodeChange
} from '@xyflow/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { XYPosition } from '@shared/types'

import type { Positions } from '../lib/layout'
import type { GraphModel } from '../lib/treeToGraph'
import type { FocusRequest } from '../state/useProjectGraph'
import { FileNode, FolderNode, RootNode, type GraphFlowNode, type GraphNodeData } from './nodes'

const nodeTypes = { root: RootNode, folder: FolderNode, file: FileNode }

export interface GraphCanvasProps {
  model: GraphModel
  placements: Positions
  selectedId: string | null
  focus: FocusRequest | null
  busyId: string | null
  hits: ReadonlySet<string>
  visited: ReadonlySet<string>
  dimmed: boolean
  onSelect: (nodeId: string | null) => void
  onToggle: (refId: string) => void
  onMove: (nodeId: string, position: XYPosition) => void
}

export function GraphCanvas(props: GraphCanvasProps) {
  return (
    <ReactFlowProvider>
      <Canvas {...props} />
    </ReactFlowProvider>
  )
}

function Canvas({
  model,
  placements,
  selectedId,
  focus,
  busyId,
  hits,
  visited,
  dimmed,
  onSelect,
  onToggle,
  onMove
}: GraphCanvasProps) {
  const { fitView } = useReactFlow()
  const [dragging, setDragging] = useState<Record<string, XYPosition>>({})
  const focusHandled = useRef(0)

  const nodes = useMemo<GraphFlowNode[]>(() => {
    return model.nodes.map((node) => {
      const selected = selectedId === node.id
      const hit = hits.has(node.id)
      const data: GraphNodeData = {
        node,
        selected,
        hit,
        visited: visited.has(node.id),
        busy: busyId === node.refId,
        onToggle
      }
      return {
        id: node.id,
        type: node.kind,
        position: dragging[node.id] ?? placements[node.id] ?? { x: 0, y: 0 },
        data,
        draggable: true,
        selectable: false,
        className: dimmed && !hit ? 'node-dimmed' : undefined
      }
    })
  }, [model, placements, dragging, selectedId, hits, visited, busyId, onToggle, dimmed])

  const edges = useMemo<Edge[]>(() => model.edges.map((edge) => ({ ...edge, type: 'smoothstep' })), [model])

  const handleNodesChange = useCallback((changes: NodeChange<GraphFlowNode>[]) => {
    const moved: Record<string, XYPosition> = {}
    for (const change of changes) {
      if (change.type === 'position' && change.position) moved[change.id] = change.position
    }
    if (Object.keys(moved).length > 0) setDragging((current) => ({ ...current, ...moved }))
  }, [])

  const handleDragStop = useCallback(
    (_event: unknown, node: GraphFlowNode) => {
      onMove(node.id, node.position)
      setDragging((current) => {
        const next = { ...current }
        delete next[node.id]
        return next
      })
    },
    [onMove]
  )

  useEffect(() => {
    if (!focus || focusHandled.current === focus.nonce) return
    if (!model.nodes.some((node) => node.id === focus.nodeId)) return
    focusHandled.current = focus.nonce
    void fitView({ nodes: [{ id: focus.nodeId }], duration: 320, padding: 2, maxZoom: 1 })
  }, [focus, model, fitView])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={handleNodesChange}
      onNodeClick={(_event, node) => onSelect(node.id)}
      onNodeDragStop={handleDragStop}
      onPaneClick={() => onSelect(null)}
      nodesConnectable={false}
      elementsSelectable={false}
      minZoom={0.15}
      maxZoom={1.75}
      fitView
      fitViewOptions={{ padding: 0.22 }}
      defaultEdgeOptions={{ type: 'smoothstep', style: { stroke: 'var(--line-strong)', strokeWidth: 1 } }}
    >
      <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#e3e3df" />
      <MiniMap
        pannable
        zoomable
        nodeColor={(node) => (node.id.startsWith('file:') ? '#f1f1ef' : '#d3d3ce')}
        maskColor="rgba(255, 255, 255, 0.72)"
      />
      <Controls showInteractive={false} />
    </ReactFlow>
  )
}
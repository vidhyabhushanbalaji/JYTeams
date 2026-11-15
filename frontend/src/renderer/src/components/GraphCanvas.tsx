/**
 * The tree canvas.
 *
 * Nodes live in React Flow state and are rebuilt only when the view or its flags change, so
 * a drag mutates one node object and nothing else. Selection is handled by us (not React
 * Flow) and touches only the two cards whose flag changed, which keeps it out of the drag
 * path entirely.
 */

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  useNodesState,
  useReactFlow,
  type Edge,
  type NodeChange
} from '@xyflow/react'
import { useCallback, useEffect, useMemo, useRef } from 'react'

import type { XYPosition } from '@shared/types'

import type { FocusViewModel } from '../lib/focusGraph'
import type { FocusRequest } from '../state/useFocusGraph'
import { TreeEdge } from './TreeEdge'
import { CentreNode, FileNode, FolderNode, type GraphFlowNode, type GraphNodeData } from './nodes'

const nodeTypes = { centre: CentreNode, folder: FolderNode, file: FileNode }
const edgeTypes = { branch: TreeEdge }

export interface GraphCanvasProps {
  model: FocusViewModel
  placements: Record<string, XYPosition>
  /** Changes when the view or its flags change - never during a drag. */
  graphKey: string
  /** Changes only when you move to another folder. */
  viewKey: string
  selectedId: string | null
  focus: FocusRequest | null
  busyId: string | null
  hits: ReadonlySet<string>
  dimmed: boolean
  onSelect: (nodeId: string | null) => void
  onOpen: (refId: string) => void
  /** Double-clicking a file card opens its markdown in the document sheet. */
  onOpenFile: (refId: string) => void
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
  graphKey,
  viewKey,
  selectedId,
  focus,
  busyId,
  hits,
  dimmed,
  onSelect,
  onOpen,
  onOpenFile,
  onMove
}: GraphCanvasProps) {
  const { fitView } = useReactFlow()
  const [nodes, setNodes] = useNodesState<GraphFlowNode>([])

  // Pressing a card is one gesture with two meanings: select, then open. Reading the live
  // props through a ref keeps the callback stable, so cards never hold a stale closure.
  const live = useRef({ model, selectedId, onOpen, onSelect, onOpenFile })
  live.current = { model, selectedId, onOpen, onSelect, onOpenFile }

  const activate = useCallback((refId: string) => {
    const current = live.current
    const node = current.model.nodes.find((entry) => entry.refId === refId)
    if (!node) return
    if (node.navigable && current.selectedId === node.id) {
      current.onOpen(node.refId)
      return
    }
    current.onSelect(node.id)
  }, [])

  // A double-click is only meaningful on a document; folders already open on the second press.
  const openDocument = useCallback((refId: string) => {
    const current = live.current
    const node = current.model.nodes.find((entry) => entry.refId === refId)
    if (node?.kind === 'file') current.onOpenFile(node.refId)
  }, [])

  const builtFor = useRef('')
  const fittedFor = useRef('')
  const focusHandled = useRef(0)

  const hitKey = useMemo(() => [...hits].sort().join(','), [hits])
  const rebuildKey = `${graphKey}|${hitKey}|${dimmed ? 1 : 0}|${busyId ? busyId : '-'}`

  useEffect(() => {
    if (builtFor.current === rebuildKey) return
    builtFor.current = rebuildKey
    setNodes(
      model.nodes.map((node) => ({
        id: node.id,
        type: node.kind,
        position: placements[node.id] ?? { x: 0, y: 0 },
        data: {
          node,
          hit: hits.has(node.id),
          dimmed: dimmed && !hits.has(node.id),
          busy: busyId === node.refId,
          selected: selectedId === node.id,
          onActivate: activate
        },
        draggable: true,
        selectable: false
      }))
    )
  }, [rebuildKey, model, placements, hits, dimmed, busyId, selectedId, activate, setNodes])

  // Selecting a card replaces at most two node objects; the array is never rebuilt.
  useEffect(() => {
    setNodes((current) =>
      current.map((node) => {
        const selected = node.id === selectedId
        if (Boolean(node.data.selected) === selected) return node
        return { ...node, data: { ...node.data, selected } }
      })
    )
  }, [selectedId, setNodes])

  const edges = useMemo<Edge[]>(() => model.edges.map((edge) => ({ ...edge, type: 'branch' })), [model])

  const handleNodesChange = useCallback(
    (changes: NodeChange<GraphFlowNode>[]) => setNodes((current) => applyNodeChanges(changes, current)),
    [setNodes]
  )

  // A plain click also ends a zero-distance drag; only a real move is worth persisting.
  const dragOrigin = useRef<{ id: string; x: number; y: number } | null>(null)

  const handleDragStart = useCallback((_event: unknown, node: GraphFlowNode) => {
    dragOrigin.current = { id: node.id, x: node.position.x, y: node.position.y }
  }, [])

  const handleDragStop = useCallback(
    (_event: unknown, node: GraphFlowNode) => {
      const origin = dragOrigin.current
      dragOrigin.current = null
      if (
        origin &&
        origin.id === node.id &&
        Math.abs(node.position.x - origin.x) < 1 &&
        Math.abs(node.position.y - origin.y) < 1
      ) {
        return
      }
      onMove(node.id, node.position)
    },
    [onMove]
  )

  // Re-centre when you move to another folder (but never mid-drag).
  useEffect(() => {
    if (fittedFor.current === viewKey) return
    fittedFor.current = viewKey
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer = window.setTimeout(() => {
      void fitView({ duration: reduced ? 0 : 280, padding: 0.18, maxZoom: 1.08 })
    }, 60)
    return () => window.clearTimeout(timer)
  }, [viewKey, fitView])

  // An explicit request - a search hit or a freshly placed document.
  useEffect(() => {
    if (!focus || focusHandled.current === focus.nonce) return
    if (!nodes.some((node) => node.id === focus.nodeId)) return
    focusHandled.current = focus.nonce
    void fitView({ nodes: [{ id: focus.nodeId }], duration: 320, padding: 2, maxZoom: 1 })
  }, [focus, nodes, fitView])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={handleNodesChange}
      onNodeClick={(_event, node) => activate(node.data.node.refId)}
      onNodeDoubleClick={(_event, node) => openDocument(node.data.node.refId)}
      onNodeDragStart={handleDragStart}
      onNodeDragStop={handleDragStop}
      onPaneClick={() => onSelect(null)}
      nodesConnectable={false}
      elementsSelectable={false}
      minZoom={0.12}
      maxZoom={1.8}
      fitView
      fitViewOptions={{ padding: 0.18, maxZoom: 1.08 }}
      defaultEdgeOptions={{ type: 'branch' }}
    >
      <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#e3e3df" />
      <MiniMap
        pannable
        zoomable
        style={{ width: 132, height: 96 }}
        offsetScale={16}
        nodeColor={(node) =>
          (node.data as GraphNodeData | undefined)?.node?.kind === 'centre' ? '#191919' : '#d3d3ce'
        }
        nodeStrokeWidth={0}
        nodeBorderRadius={2}
        maskColor="rgba(255, 255, 255, 0.82)"
        ariaLabel="Project map"
      />
      <Controls showInteractive={false} />
    </ReactFlow>
  )
}

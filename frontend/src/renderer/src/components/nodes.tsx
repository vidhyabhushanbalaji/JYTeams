/** The three card types the canvas draws. Nothing here fetches: every node is a pure
 *  function of the model the graph hook produced. */

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { memo } from 'react'

import type { GraphNodeModel } from '../lib/treeToGraph'

export interface GraphNodeData extends Record<string, unknown> {
  node: GraphNodeModel
  selected: boolean
  hit: boolean
  visited: boolean
  busy: boolean
  onToggle: (refId: string) => void
}

export type GraphFlowNode = Node<GraphNodeData>

function classes(data: GraphNodeData, kind: string, extra: string[] = []): string {
  return [
    'node',
    `node--${kind}`,
    data.selected ? 'node--selected' : '',
    data.hit ? 'node--hit' : '',
    data.visited ? 'node--visited' : '',
    ...extra
  ]
    .filter(Boolean)
    .join(' ')
}

function Chevron({ node, busy, onToggle }: { node: GraphNodeModel; busy: boolean; onToggle: (refId: string) => void }) {
  return (
    <button
      type="button"
      className="node__chevron"
      aria-label={node.expanded ? `Collapse ${node.label}` : `Expand ${node.label}`}
      aria-expanded={node.expanded}
      onClick={(event) => {
        event.stopPropagation()
        onToggle(node.refId)
      }}
    >
      {busy ? <span className="spinner" /> : node.expanded ? '\u25be' : '\u25b8'}
    </button>
  )
}

function FolderGlyph() {
  return (
    <span className="node__glyph" aria-hidden="true">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
        <path d="M2 5.2c0-.55.45-1 1-1h3l1.2 1.4H13c.55 0 1 .45 1 1v5.2c0 .55-.45 1-1 1H3c-.55 0-1-.45-1-1Z" />
      </svg>
    </span>
  )
}

function PageGlyph() {
  return (
    <span className="node__glyph" aria-hidden="true">
      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
        <path d="M4 2.5h5L12.5 6v7.5h-8.5Z" />
        <path d="M9 2.5V6h3.5" />
      </svg>
    </span>
  )
}

export const FolderNode = memo(function FolderNode({ data }: NodeProps<GraphFlowNode>) {
  const { node, busy, onToggle } = data
  return (
    <div className={classes(data, 'folder')}>
      <Handle type="target" position={Position.Left} className="node__handle" isConnectable={false} />
      <div className="node__head">
        <Chevron node={node} busy={busy} onToggle={onToggle} />
        <span className="node__name">{node.label}</span>
        {node.fileCount > 0 ? <span className="node__count">{node.fileCount}</span> : null}
      </div>
      <p className={node.description ? 'node__desc' : 'node__desc node__desc--empty'}>
        {node.description ?? 'No description yet'}
      </p>
      <div className="node__footer">
        <span>{node.fileCount} files</span>
        <span className="node__sep" />
        <span>{node.directoryCount} folders</span>
        {node.hiddenDirectories > 0 ? <span className="node__chip">+{node.hiddenDirectories}</span> : null}
      </div>
      <Handle type="source" position={Position.Right} className="node__handle" isConnectable={false} />
    </div>
  )
})

export const RootNode = memo(function RootNode({ data }: NodeProps<GraphFlowNode>) {
  const { node } = data
  return (
    <div className={classes(data, 'root')}>
      <Handle type="target" position={Position.Left} className="node__handle" isConnectable={false} />
      <div className="node__head">
        <FolderGlyph />
        <span className="node__name">{node.label}</span>
      </div>
      <p className={node.description ? 'node__desc' : 'node__desc node__desc--empty'}>
        {node.description ?? 'This project has no description yet'}
      </p>
      <div className="node__footer">
        <span>{node.fileCount} files</span>
        <span className="node__sep" />
        <span>{node.directoryCount} folders</span>
      </div>
      <Handle type="source" position={Position.Right} className="node__handle" isConnectable={false} />
    </div>
  )
})

export const FileNode = memo(function FileNode({ data }: NodeProps<GraphFlowNode>) {
  const { node } = data
  return (
    <div className={classes(data, 'file')}>
      <Handle type="target" position={Position.Left} className="node__handle" isConnectable={false} />
      <div className="node__head">
        <PageGlyph />
        <span className="node__name">{node.label}</span>
      </div>
      <p className={node.description ? 'node__desc' : 'node__desc node__desc--empty'}>
        {node.description ?? 'No summary yet'}
      </p>
      <div className="node__footer">
        <span>{node.sizeBytes ? `${Math.max(1, Math.round(node.sizeBytes / 1024))} KB` : 'file'}</span>
        {node.status && node.status !== 'ok' ? (
          <span className={`node__status node__status--${node.status}`}>{node.status}</span>
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} className="node__handle" isConnectable={false} />
    </div>
  )
})
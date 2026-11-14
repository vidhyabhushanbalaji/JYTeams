/** The three cards on the tree: the centre folder, its files, its subfolders.
 *
 * A folder is a two-step card: the first press selects it (the inspector describes it), the
 * second opens it. The canvas decides which of the two a press means, so the card only has
 * to report that it was activated.
 */

import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { memo, type KeyboardEvent } from 'react'

import { humanBytes } from '../lib/format'
import type { FocusNodeModel } from '../lib/focusGraph'

export interface GraphNodeData extends Record<string, unknown> {
  node: FocusNodeModel
  hit: boolean
  dimmed: boolean
  busy: boolean
  selected: boolean
  onActivate: (refId: string) => void
}

export type GraphFlowNode = Node<GraphNodeData>

function cardClass(data: GraphNodeData, kind: string): string {
  return [
    'node',
    `node--${kind}`,
    data.selected ? 'node--selected' : '',
    data.hit ? 'node--hit' : '',
    data.dimmed ? 'node--dim' : ''
  ]
    .filter(Boolean)
    .join(' ')
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

function keyboardActivate(value: GraphNodeData): (event: KeyboardEvent<HTMLDivElement>) => void {
  return (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      value.onActivate(value.node.refId)
    }
  }
}

export const CentreNode = memo(function CentreNode({ data }: NodeProps<GraphFlowNode>) {
  const { node } = data
  return (
    <div
      className={cardClass(data, 'centre')}
      role="button"
      tabIndex={0}
      aria-label={`${node.label}, current folder`}
      onKeyDown={keyboardActivate(data)}
    >
      <Handle type="target" position={Position.Left} className="node__handle" isConnectable={false} />
      <div className="node__head">
        <FolderGlyph />
        <span className="node__name">{node.label}</span>
      </div>
      <p className={node.description ? 'node__desc' : 'node__desc node__desc--empty'}>
        {node.description ?? 'This folder has no description yet'}
      </p>
      <div className="node__footer">
        <span>{node.fileCount} files</span>
        <span className="node__sep" />
        <span>{node.directoryCount} folders</span>
        <span className="node__chip">centre</span>
      </div>
      <Handle type="source" position={Position.Right} className="node__handle" isConnectable={false} />
    </div>
  )
})

export const FolderNode = memo(function FolderNode({ data }: NodeProps<GraphFlowNode>) {
  const { node, busy, selected } = data
  return (
    <div
      className={cardClass(data, 'folder')}
      role="button"
      tabIndex={0}
      aria-label={selected ? `Open ${node.label}` : `Select ${node.label}`}
      onKeyDown={keyboardActivate(data)}
    >
      <Handle type="target" position={Position.Left} className="node__handle" isConnectable={false} />
      <div className="node__head">
        <FolderGlyph />
        <span className="node__name">{node.label}</span>
        <span className={`node__open${selected ? ' node__open--ready' : ''}`} aria-hidden="true">
          {busy ? <span className="spinner" /> : selected ? 'Open' : '\u203a'}
        </span>
      </div>
      <p className={node.description ? 'node__desc' : 'node__desc node__desc--empty'}>
        {node.description ?? 'No description yet'}
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
    <div
      className={cardClass(data, 'file')}
      role="button"
      tabIndex={0}
      aria-label={`Select ${node.label}`}
      onKeyDown={keyboardActivate(data)}
    >
      <Handle type="target" position={Position.Left} className="node__handle" isConnectable={false} />
      <div className="node__head">
        <PageGlyph />
        <span className="node__name">{node.label}</span>
      </div>
      <p className={node.description ? 'node__desc' : 'node__desc node__desc--empty'}>
        {node.description ?? 'No summary yet'}
      </p>
      <div className="node__footer">
        <span>{humanBytes(node.sizeBytes ?? 0)}</span>
        {node.status && node.status !== 'ok' ? (
          <span className={`node__status node__status--${node.status}`}>{node.status}</span>
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} className="node__handle" isConnectable={false} />
    </div>
  )
})
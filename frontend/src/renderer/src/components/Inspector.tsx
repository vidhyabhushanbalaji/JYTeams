import type { GraphNodeModel } from '../lib/treeToGraph'
import { humanBytes } from '../lib/format'

export function Inspector({ node }: { node: GraphNodeModel | null }) {
  if (!node) {
    return (
      <div className="side__body">
        <div className="side__section">
          <span className="side__label">Nothing selected</span>
          <p className="side__text">
            Pick a card to read its description and counts. Drag cards to rearrange the graph, and
            use a folder's chevron to look inside it.
          </p>
        </div>
        <div className="side__section">
          <span className="side__label">The three levels</span>
          <p className="side__empty">
            The root and two levels of folders are drawn when a project opens. Anything deeper
            appears when you expand the folder that holds it.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="side__body">
      <div className="side__section">
        <span className="side__label">
          {node.kind === 'file' ? 'Document' : node.kind === 'root' ? 'Project root' : 'Folder'}
        </span>
        <h3 className="side__title">{node.label}</h3>
      </div>

      <div className="side__section">
        <span className="side__label">{node.kind === 'file' ? 'Summary' : 'Description'}</span>
        <p className="side__text">{node.description ?? 'Nothing written for this yet.'}</p>
      </div>

      <div className="kv">
        <div className="kv__row">
          <span className="kv__key">Path</span>
          <span className="kv__value">{node.path || '(project root)'}</span>
        </div>
        {node.kind === 'file' ? (
          <div className="kv__row">
            <span className="kv__key">Size</span>
            <span className="kv__value">{humanBytes(node.sizeBytes ?? 0)}</span>
          </div>
        ) : null}
        {node.kind === 'file' ? (
          <div className="kv__row">
            <span className="kv__key">Summary</span>
            <span className="kv__value">{node.status ?? 'pending'}</span>
          </div>
        ) : (
          <> 
            <div className="kv__row">
              <span className="kv__key">Files</span>
              <span className="kv__value">{node.fileCount} direct</span>
            </div>
            <div className="kv__row">
              <span className="kv__key">Folders</span>
              <span className="kv__value">{node.directoryCount} direct</span>
            </div>
          </>
        )}
        {node.hiddenDirectories > 0 ? (
          <div className="kv__row">
            <span className="kv__key">Hidden</span>
            <span className="kv__value">{node.hiddenDirectories} child folders</span>
          </div>
        ) : null}
      </div>
    </div>
  )
}
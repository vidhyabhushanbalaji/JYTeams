import { humanBytes } from '../lib/format'
import type { FocusNodeModel } from '../lib/focusGraph'

export function Inspector({ node }: { node: FocusNodeModel | null }) {
  if (!node) {
    return (
      <div className="side__body">
        <div className="side__section">
          <span className="side__label">Nothing selected</span>
          <p className="side__text">
            Pick a card to read its description and counts. Press a folder once to select it and
            again to open it; drag cards to rearrange the tree.
          </p>
        </div>
        <div className="side__section">
          <span className="side__label">How the tree works</span>
          <p className="side__empty">
            One folder sits at the top. Its files hang from short branches just below it, and its
            subfolders from longer branches further down; nothing deeper is drawn until you open a
            folder, and Back returns you to the previous one.
          </p>
        </div>
      </div>
    )
  }

  const kindLabel = node.kind === 'file' ? 'Document' : node.kind === 'centre' ? 'Current folder' : 'Folder'

  return (
    <div className="side__body">
      <div className="side__section">
        <span className="side__label">{kindLabel}</span>
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
          <>
            <div className="kv__row">
              <span className="kv__key">Size</span>
              <span className="kv__value">{humanBytes(node.sizeBytes ?? 0)}</span>
            </div>
            <div className="kv__row">
              <span className="kv__key">Summary</span>
              <span className="kv__value">{node.status ?? 'pending'}</span>
            </div>
          </>
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

        {node.navigable ? (
          <div className="kv__row">
            <span className="kv__key">Press</span>
            <span className="kv__value">again to open this folder</span>
          </div>
        ) : null}
      </div>
    </div>
  )
}
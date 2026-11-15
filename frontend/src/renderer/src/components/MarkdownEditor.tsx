import { Markdown } from '../lib/markdown'

export type MarkdownMode = 'read' | 'edit'

/**
 * The Read/Edit switch, shared by the document sheet and the new-document editor.
 *
 * It is separate from the body so a caller can put it where it belongs: the sheet keeps it in
 * its header, the wizard puts it on the editor's toolbar.
 */
export function EditorTabs({
  mode,
  onChange,
  label = 'Document mode'
}: {
  mode: MarkdownMode
  onChange: (mode: MarkdownMode) => void
  label?: string
}) {
  return (
    <div className="sheet__tabs" role="tablist" aria-label={label}>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'read'}
        className={`tab${mode === 'read' ? ' tab--active' : ''}`}
        onClick={() => onChange('read')}
      >
        Read
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'edit'}
        className={`tab${mode === 'edit' ? ' tab--active' : ''}`}
        onClick={() => onChange('edit')}
      >
        Edit
      </button>
    </div>
  )
}

/**
 * One markdown body: a plain textarea while editing, rendered markdown while reading.
 *
 * A document stored as text is edited faithfully as text, so there is no WYSIWYG layer and no
 * markdown dependency — the renderer is `lib/markdown.tsx`, which builds React elements rather
 * than an HTML string.
 */
export function MarkdownEditor({
  value,
  onChange,
  mode,
  label,
  placeholder,
  autoFocus = false
}: {
  value: string
  onChange: (text: string) => void
  mode: MarkdownMode
  /** Names the textarea for assistive technology. */
  label: string
  placeholder?: string
  autoFocus?: boolean
}) {
  if (mode === 'edit') {
    return (
      <textarea
        className="md-editor"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label={label}
        placeholder={placeholder}
        spellCheck
        autoFocus={autoFocus}
      />
    )
  }

  return (
    <article className="md">
      <Markdown text={value} />
    </article>
  )
}

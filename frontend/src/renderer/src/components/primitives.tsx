import { useEffect, type ReactNode } from 'react'

export function Dialog({
  open,
  title,
  subtitle,
  wide = false,
  onClose,
  children,
  footer
}: {
  open: boolean
  title: string
  subtitle?: string
  /** A wider panel for content that needs room, such as the markdown editor. */
  wide?: boolean
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="dialog"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        className={wide ? 'dialog__panel dialog__panel--wide' : 'dialog__panel'}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="dialog__head">
          <div>
            <h2 className="dialog__title">{title}</h2>
            {subtitle ? <p className="dialog__sub">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            className="dialog__close btn btn--ghost btn--icon"
            onClick={onClose}
            aria-label="Close"
          >
            {'\u00d7'}
          </button>
        </header>
        <div className="dialog__body">{children}</div>
        {footer ? <footer className="dialog__foot">{footer}</footer> : null}
      </div>
    </div>
  )
}

export function Field({
  label,
  hint,
  children
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {children}
      {hint ? <span className="field__hint">{hint}</span> : null}
    </label>
  )
}

export function Spinner({ label = 'Working' }: { label?: string }) {
  return <span className="spinner" role="status" aria-label={label} />
}

export function ErrorBox({
  title,
  detail,
  children
}: {
  title: string
  detail: string
  children?: ReactNode
}) {
  return (
    <div className="error-box">
      <p className="error-box__title">{title}</p>
      <p className="error-box__detail">{detail}</p>
      {children}
    </div>
  )
}

export function Empty({ title, text, children }: { title: string; text: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h2 className="empty__title">{title}</h2>
      <p className="empty__text">{text}</p>
      {children}
    </div>
  )
}
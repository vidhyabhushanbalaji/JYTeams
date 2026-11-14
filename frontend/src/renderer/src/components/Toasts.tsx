import type { ToastMessage } from '../state/useToasts'

export function Toasts({
  toasts,
  onDismiss
}: {
  toasts: ToastMessage[]
  onDismiss: (id: number) => void
}) {
  if (toasts.length === 0) return null
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast${toast.tone === 'error' ? ' toast--error' : ''}`}>
          <span>{toast.message}</span>
          <button type="button" onClick={() => onDismiss(toast.id)} aria-label="Dismiss">
            {'\u00d7'}
          </button>
        </div>
      ))}
    </div>
  )
}
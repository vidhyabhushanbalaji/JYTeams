import { useCallback, useState } from 'react'

export type ToastTone = 'info' | 'error'

export interface ToastMessage {
  id: number
  message: string
  tone: ToastTone
}

export function useToasts() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = Date.now() + Math.random()
    setToasts((current) => [...current, { id, message, tone }])
    window.setTimeout(() => dismiss(id), tone === 'error' ? 8000 : 4500)
  }, [dismiss])

  return { toasts, notify, dismiss }
}
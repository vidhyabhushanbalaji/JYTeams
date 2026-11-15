/**
 * A project's chat: load the newest page, then poll with a `seq` cursor.
 *
 * Polling (rather than a socket) is deliberate: the renderer has no network access and no socket,
 * and one small read every few seconds is simpler to own than a WebSocket bridge through the
 * Electron main process. The poll pauses while the window is hidden and resumes on return.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import type { ApiError, ChatMessage } from '@shared/types'

import { lastSeq, mergeMessages } from '../lib/chat'

const POLL_MS = 3_000
const PAGE_SIZE = 60

export type ChatStatus = 'idle' | 'loading' | 'ready' | 'error'

export function useChat(projectId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [status, setStatus] = useState<ChatStatus>('idle')
  const [error, setError] = useState<ApiError | null>(null)
  const [sending, setSending] = useState(false)
  const messagesRef = useRef<ChatMessage[]>([])
  messagesRef.current = messages
  const projectRef = useRef<string | null>(projectId)
  projectRef.current = projectId

  const loadPage = useCallback(async (): Promise<void> => {
    if (!projectId) return
    setStatus('loading')
    setError(null)
    const result = await window.jyteams.chat.messages({ projectId, limit: PAGE_SIZE })
    if (projectRef.current !== projectId) return
    if (result.ok) {
      setMessages(result.data)
      setStatus('ready')
    } else {
      setMessages([])
      setError(result.error)
      setStatus('error')
    }
  }, [projectId])

  const poll = useCallback(async (): Promise<void> => {
    if (!projectId) return
    const cursor = lastSeq(messagesRef.current)
    const result = await window.jyteams.chat.messages({
      projectId,
      afterSeq: cursor > 0 ? cursor : undefined,
      limit: 200
    })
    if (projectRef.current !== projectId) return
    if (result.ok) {
      setMessages((current) => mergeMessages(current, result.data))
      setStatus('ready')
    } else {
      setError(result.error)
    }
  }, [projectId])

  useEffect(() => {
    if (!projectId) {
      setMessages([])
      setStatus('idle')
      setError(null)
      return
    }
    void loadPage()
    const timer = setInterval(() => {
      if (!document.hidden) void poll()
    }, POLL_MS)
    const onVisible = (): void => {
      if (!document.hidden) void poll()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [projectId, loadPage, poll])

  const send = useCallback(
    async (body: string): Promise<boolean> => {
      if (!projectId) return false
      setSending(true)
      setError(null)
      const result = await window.jyteams.chat.post(projectId, body)
      setSending(false)
      if (!result.ok) {
        setError(result.error)
        return false
      }
      setMessages((current) => mergeMessages(current, [result.data]))
      setStatus('ready')
      return true
    },
    [projectId]
  )

  const remove = useCallback(
    async (messageId: string): Promise<boolean> => {
      const result = await window.jyteams.chat.remove(messageId)
      if (!result.ok) {
        setError(result.error)
        return false
      }
      await loadPage()
      return true
    },
    [loadPage]
  )

  return { messages, status, error, sending, send, remove, reload: loadPage }
}

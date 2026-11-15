/**
 * The chat API: a project's group chat, its messages and the composer's mention targets.
 *
 * New messages arrive by polling with a `seq` cursor (see `useChat`): the renderer has no socket
 * and no direct network access, and one small read every few seconds is simpler than pushing
 * events through the Electron main process.
 */

import type { ChatChannel, ChatMessage, MentionTarget } from '../../shared/types'
import { request, requestVoid } from './client'

const BASE = '/api/chat'
const JSON_HEADERS = { 'Content-Type': 'application/json' }
const id = encodeURIComponent

export const listChannels = (): Promise<ChatChannel[]> => request(`${BASE}/channels`)

export function listMessages(input: {
  projectId: string
  afterSeq?: number
  limit?: number
}): Promise<ChatMessage[]> {
  const params = new URLSearchParams({ limit: String(input.limit ?? 50) })
  if (typeof input.afterSeq === 'number') params.set('after_seq', String(input.afterSeq))
  return request(`${BASE}/projects/${id(input.projectId)}/messages?${params.toString()}`)
}

export const postMessage = (projectId: string, body: string): Promise<ChatMessage> =>
  request(`${BASE}/projects/${id(projectId)}/messages`, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ body })
  })

export const deleteMessage = (messageId: string): Promise<null> =>
  requestVoid(`${BASE}/messages/${id(messageId)}`, { method: 'DELETE' })

export function listMentionTargets(input: {
  projectId: string
  query?: string
  limit?: number
}): Promise<MentionTarget[]> {
  const params = new URLSearchParams({ q: input.query ?? '', limit: String(input.limit ?? 20) })
  return request(`${BASE}/projects/${id(input.projectId)}/mention-targets?${params.toString()}`)
}

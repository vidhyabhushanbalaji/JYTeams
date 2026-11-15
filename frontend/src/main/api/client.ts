/**
 * The only place the desktop app talks HTTP.
 *
 * Requests run in the main process, which keeps the renderer free of CORS (a packaged
 * Electron window is a `file://` origin, so a direct fetch would be rejected by the API)
 * and lets a whole folder be read from disk without crossing IPC.
 */

import type { ApiError, ApiResult } from '../../shared/types'
import { readConfig } from '../config'

export const DEFAULT_TIMEOUT_MS = 120_000
/**
 * Creation describes one folder per model call and a placement refreshes its descriptions in one
 * call, so those are the requests that can legitimately take minutes. The suggestion scan and
 * every search are local.
 */
export const LONG_TIMEOUT_MS = 600_000

export class HttpError extends Error {
  readonly status: number
  readonly detail: unknown

  constructor(status: number, message: string, detail: unknown) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.detail = detail
  }
}

function authHeaders(): Record<string, string> {
  const config = readConfig()
  if (config.bearerToken) return { Authorization: `Bearer ${config.bearerToken}` }
  if (config.devUserId) return { 'X-Dev-User-Id': config.devUserId }
  return {}
}

export function apiUrl(path: string): string {
  return `${readConfig().baseUrl}${path}`
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return (await response.clone().json()) as unknown
  } catch {
    return null
  }
}

function detailOf(body: unknown): unknown {
  if (body && typeof body === 'object' && 'detail' in body) {
    return (body as { detail: unknown }).detail
  }
  return body
}

function messageFrom(status: number, body: unknown): string {
  const detail = detailOf(body)
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail === 'object') {
    const message = (detail as Record<string, unknown>).message
    if (typeof message === 'string' && message.trim()) return message
  }
  if (status === 401) return 'The backend rejected this identity. Check Settings.'
  if (status === 404) return 'That record does not exist in this project any more.'
  if (status === 503) return 'The backend is running, but Supabase is not configured yet.'
  return `The backend answered HTTP ${status}.`
}

function unreachable(error: unknown): string {
  const reason = error instanceof Error ? error.message : String(error)
  const { baseUrl } = readConfig()
  return `Cannot reach the API at ${baseUrl}. Start it from backend/ with "uvicorn app.main:app --reload --port 8000". (${reason})`
}

export interface RequestOptions extends Omit<RequestInit, 'signal'> {
  timeoutMs?: number
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...rest } = options
  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      ...rest,
      headers: { Accept: 'application/json', ...authHeaders(), ...(headers as Record<string, string> | undefined) },
      signal: AbortSignal.timeout(timeoutMs)
    })
  } catch (error) {
    throw new HttpError(0, unreachable(error), null)
  }

  const body = await readJson(response)
  if (!response.ok) throw new HttpError(response.status, messageFrom(response.status, body), detailOf(body))
  if (body === null) throw new HttpError(response.status, 'The backend returned an empty response.', null)
  return body as T
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof HttpError) {
    return { status: error.status, message: error.message, detail: error.detail }
  }
  return { status: 0, message: error instanceof Error ? error.message : String(error), detail: null }
}

/** Run a call and hand the renderer a value or a normalised error - never a throw. */
export async function run<T>(work: () => Promise<T>): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await work() }
  } catch (error) {
    return { ok: false, error: toApiError(error) }
  }
}
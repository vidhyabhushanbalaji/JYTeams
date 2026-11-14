/** Two probes: the process itself, then whether Supabase is configured and reachable. */

import type { HealthReport } from '../../shared/types'
import { apiUrl } from './client'

async function body(response: Response): Promise<Record<string, unknown> | null> {
  try {
    return (await response.json()) as Record<string, unknown>
  } catch {
    return null
  }
}

export async function ping(): Promise<HealthReport> {
  let api = false
  let apiDetail = ''

  try {
    const response = await fetch(apiUrl('/health'), { signal: AbortSignal.timeout(4000) })
    api = response.ok
    apiDetail = response.ok ? 'reachable' : `HTTP ${response.status}`
  } catch (error) {
    apiDetail = error instanceof Error ? error.message : 'unreachable'
  }

  if (!api) return { api: false, supabase: false, apiDetail, supabaseDetail: 'not checked' }

  try {
    const response = await fetch(apiUrl('/health/supabase'), { signal: AbortSignal.timeout(8000) })
    const payload = await body(response)
    const detail = payload?.detail
    return {
      api: true,
      supabase: response.ok,
      apiDetail,
      supabaseDetail: typeof detail === 'string' ? detail : response.ok ? 'reachable' : `HTTP ${response.status}`
    }
  } catch (error) {
    return {
      api: true,
      supabase: false,
      apiDetail,
      supabaseDetail: error instanceof Error ? error.message : 'unreachable'
    }
  }
}
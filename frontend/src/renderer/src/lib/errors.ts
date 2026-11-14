/** Turning a normalised ApiError into words a person can act on. */

import type { AddSuggestion, ApiError } from '@shared/types'

export function describeError(error: ApiError): string {
  if (error.status === 0) return error.message
  return error.message || `The backend answered HTTP ${error.status}.`
}

function detailRecord(error: ApiError): Record<string, unknown> | null {
  const { detail } = error
  if (!detail || typeof detail !== 'object') return null
  return detail as Record<string, unknown>
}

export function suggestedNames(error: ApiError): string[] {
  const record = detailRecord(error)
  const names = record?.suggested_names
  if (!Array.isArray(names)) return []
  return names.filter((name): name is string => typeof name === 'string')
}

export function conflictPaths(error: ApiError): string[] {
  const record = detailRecord(error)
  const conflicts = record?.conflicts
  if (!Array.isArray(conflicts)) return []
  return conflicts.filter((path): path is string => typeof path === 'string')
}

export function isExpired(error: ApiError): boolean {
  return error.status === 410
}

export function isOffline(error: ApiError): boolean {
  return error.status === 0
}

/** The best free names to offer when a placement collided with an existing path. */
export function retryNames(error: ApiError, suggestion: AddSuggestion | null): string[] {
  const fromError = suggestedNames(error)
  if (fromError.length > 0) return fromError
  return suggestion?.suggested_file_names ?? []
}
/**
 * Runtime configuration for the desktop app, stored beside the app in userData.
 *
 * The backend owns the real configuration (backend/.env); this is only the address of
 * that service plus the identity the app presents to it. In `AUTH_MODE=dev` the backend
 * falls back to its own DEV_USER_ID, so leaving `devUserId` blank is the normal setup.
 */

import { app } from 'electron'
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import type { AppConfig } from '../shared/types'

export const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

const DEFAULTS: AppConfig = { baseUrl: DEFAULT_BASE_URL, devUserId: '', bearerToken: '' }

let cached: AppConfig | null = null

function configFile(): string {
  return join(app.getPath('userData'), 'config.json')
}

function clean(patch: Partial<AppConfig>): Partial<AppConfig> {
  const next: Partial<AppConfig> = {}
  if (typeof patch.baseUrl === 'string') {
    const trimmed = patch.baseUrl.trim().replace(/\/+$/, '')
    next.baseUrl = trimmed || DEFAULT_BASE_URL
  }
  if (typeof patch.devUserId === 'string') next.devUserId = patch.devUserId.trim()
  if (typeof patch.bearerToken === 'string') next.bearerToken = patch.bearerToken.trim()
  return next
}

export function readConfig(): AppConfig {
  if (cached) return cached
  try {
    const raw = JSON.parse(readFileSync(configFile(), 'utf8')) as Partial<AppConfig>
    cached = { ...DEFAULTS, ...clean(raw) }
  } catch {
    cached = { ...DEFAULTS }
  }
  return cached
}

export function writeConfig(patch: Partial<AppConfig>): AppConfig {
  cached = { ...readConfig(), ...clean(patch) }
  writeFileSync(configFile(), JSON.stringify(cached, null, 2), 'utf8')
  return cached
}
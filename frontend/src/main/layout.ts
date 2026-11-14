/**
 * Where the user dragged each card, per project.
 *
 * Stored in userData rather than the renderer's localStorage: a packaged window is a
 * `file://` origin, where storage rules differ between platforms. One small JSON file per
 * project, written on drag-stop and cleared by "Tidy layout".
 */

import { app } from 'electron'
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

import type { XYPosition } from '../shared/types'

function folder(): string {
  return join(app.getPath('userData'), 'layouts')
}

function file(projectId: string): string {
  return join(folder(), `${projectId.replace(/[^a-zA-Z0-9_-]/g, '_')}.json`)
}

export async function loadLayout(projectId: string): Promise<Record<string, XYPosition>> {
  try {
    const raw = await readFile(file(projectId), 'utf8')
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return {}
    const positions: Record<string, XYPosition> = {}
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (!value || typeof value !== 'object') continue
      const point = value as { x?: unknown; y?: unknown }
      if (typeof point.x === 'number' && typeof point.y === 'number') {
        positions[key] = { x: point.x, y: point.y }
      }
    }
    return positions
  } catch {
    return {}
  }
}

export async function saveLayout(
  projectId: string,
  positions: Record<string, XYPosition>
): Promise<void> {
  await mkdir(folder(), { recursive: true })
  await writeFile(file(projectId), JSON.stringify(positions), 'utf8')
}

export async function clearLayout(projectId: string): Promise<void> {
  await rm(file(projectId), { force: true })
}
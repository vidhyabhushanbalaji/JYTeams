/**
 * Reading a folder the user picked, without ever following a symlink out of it.
 *
 * The backend accepts loose multipart parts whose filename carries the relative path, so
 * this walk is all the packaging an upload needs. The limits mirror the backend's own
 * (MAX_UPLOAD_FILES, MAX_UPLOAD_BYTES, MAX_FILE_BYTES, MAX_DIRECTORY_DEPTH) so an obviously
 * impossible upload is refused before anything is sent.
 */

import { readdir, stat } from 'node:fs/promises'
import { basename, extname, join, relative, sep } from 'node:path'

import type { FolderPreview } from '../../shared/types'

export const MARKDOWN_EXTENSIONS = new Set(['.md', '.markdown', '.mdx'])

export const UPLOAD_LIMITS = {
  maxFiles: 2000,
  maxFileBytes: 20 * 1024 * 1024,
  maxTotalBytes: 200 * 1024 * 1024,
  maxDepth: 32
}

/** Folders that never belong to a documentation tree, and can be huge. */
const SKIPPED_FOLDERS = new Set([
  'node_modules',
  '.git',
  '.svn',
  '.hg',
  'dist',
  'out',
  'build',
  '.next',
  '.venv',
  'venv',
  '__pycache__'
])

export interface WalkedFile {
  absolutePath: string
  relativePath: string
  sizeBytes: number
}

interface WalkResult {
  files: WalkedFile[]
  totalBytes: number
  skipped: number
  problems: string[]
}

const posix = (value: string): string => value.split(sep).join('/')

async function walk(root: string): Promise<WalkResult> {
  const files: WalkedFile[] = []
  const problems: string[] = []
  const queue: Array<{ dir: string; depth: number }> = [{ dir: root, depth: 0 }]
  let totalBytes = 0
  let skipped = 0

  while (queue.length > 0) {
    const current = queue.shift()
    if (!current) break

    let entries
    try {
      entries = await readdir(current.dir, { withFileTypes: true })
    } catch {
      problems.push(`Could not read ${posix(relative(root, current.dir)) || 'the folder'}.`)
      continue
    }

    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue
      const absolutePath = join(current.dir, entry.name)
      const relativePath = posix(relative(root, absolutePath))

      if (entry.isSymbolicLink()) continue

      if (entry.isDirectory()) {
        if (SKIPPED_FOLDERS.has(entry.name)) continue
        if (current.depth + 1 > UPLOAD_LIMITS.maxDepth) {
          problems.push(`${relativePath} is deeper than ${UPLOAD_LIMITS.maxDepth} levels.`)
          continue
        }
        queue.push({ dir: absolutePath, depth: current.depth + 1 })
        continue
      }

      if (!entry.isFile()) continue
      if (!MARKDOWN_EXTENSIONS.has(extname(entry.name).toLowerCase())) {
        skipped += 1
        continue
      }

      const info = await stat(absolutePath).catch(() => null)
      if (!info) {
        problems.push(`Could not read ${relativePath}.`)
        continue
      }
      if (info.size > UPLOAD_LIMITS.maxFileBytes) {
        problems.push(`${relativePath} is larger than 20 MB and was left out.`)
        skipped += 1
        continue
      }
      if (files.length + 1 > UPLOAD_LIMITS.maxFiles) {
        problems.push(`Only the first ${UPLOAD_LIMITS.maxFiles} markdown files can be uploaded.`)
        break
      }
      if (totalBytes + info.size > UPLOAD_LIMITS.maxTotalBytes) {
        problems.push('The folder is larger than the 200 MB upload limit.')
        break
      }

      files.push({ absolutePath, relativePath, sizeBytes: info.size })
      totalBytes += info.size
    }
  }

  files.sort((left, right) => left.relativePath.localeCompare(right.relativePath))
  return { files, totalBytes, skipped, problems }
}

export async function previewFolder(folderPath: string): Promise<FolderPreview> {
  const result = await walk(folderPath)
  return {
    path: folderPath,
    name: basename(folderPath),
    fileCount: result.files.length,
    totalBytes: result.totalBytes,
    skippedCount: result.skipped,
    problems: result.problems
  }
}

export async function collectMarkdownFiles(folderPath: string): Promise<WalkedFile[]> {
  return (await walk(folderPath)).files
}
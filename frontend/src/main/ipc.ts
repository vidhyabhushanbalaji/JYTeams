/**
 * The IPC surface. Each channel is a thin adapter over one API call, so the renderer can
 * never reach the network or the disk directly and every failure arrives as an ApiResult.
 */

import { BrowserWindow, dialog, ipcMain, shell } from 'electron'
import type { IpcMainInvokeEvent, OpenDialogOptions } from 'electron'

import type {
  AppConfig,
  FileContentInput,
  PlacementInput,
  TicketInput,
  TicketPatch,
  TicketStatus,
  XYPosition
} from '../shared/types'
import { run } from './api/client'
import { readFileContent, saveFileContent } from './api/files'
import { ping } from './api/health'
import { getDirectory, getJob, getProject, getTree, listProjects } from './api/projects'
import { searchProject } from './api/search'
import {
  addComment,
  attachFile,
  createTicket,
  currentMember,
  detachFile,
  getTicket,
  listActivity,
  listMembers,
  listProjectMembers,
  listTickets,
  setStatus,
  shareProject,
  signIn,
  ticketFiles,
  unshareProject,
  updateTicket
} from './api/tickets'
import { inspectFile, inspectFolder, placeFile, suggestPlacement, uploadFolder } from './api/uploads'
import { readConfig, writeConfig } from './config'
import { clearLayout, loadLayout, saveLayout } from './layout'

const MARKDOWN_FILTERS = [{ name: 'Markdown', extensions: ['md', 'markdown', 'mdx'] }]

function ownerWindow(event: IpcMainInvokeEvent): BrowserWindow | undefined {
  return BrowserWindow.fromWebContents(event.sender) ?? undefined
}

async function openDialog(event: IpcMainInvokeEvent, options: OpenDialogOptions): Promise<string | null> {
  const owner = ownerWindow(event)
  const result = owner ? await dialog.showOpenDialog(owner, options) : await dialog.showOpenDialog(options)
  if (result.canceled || result.filePaths.length === 0) return null
  return result.filePaths[0]
}

export function registerIpc(): void {
  ipcMain.handle('config:get', () => readConfig())
  ipcMain.handle('config:set', (_event, patch: Partial<AppConfig>) => writeConfig(patch))

  ipcMain.handle('health:ping', () => ping())

  ipcMain.handle('projects:list', () => run(listProjects))
  ipcMain.handle('projects:get', (_event, projectId: string) => run(() => getProject(projectId)))
  ipcMain.handle('projects:tree', (_event, projectId: string, depth: number) =>
    run(() => getTree(projectId, depth))
  )
  ipcMain.handle('projects:directory', (_event, directoryId: string) =>
    run(() => getDirectory(directoryId))
  )
  ipcMain.handle('projects:job', (_event, jobId: string) => run(() => getJob(jobId)))

  ipcMain.handle('files:read', (_event, fileId: string) => run(() => readFileContent(fileId)))
  ipcMain.handle('files:save', (_event, input: FileContentInput) =>
    run(() => saveFileContent(input.fileId, input))
  )

  ipcMain.handle('layout:load', (_event, projectId: string) => loadLayout(projectId))
  ipcMain.handle('layout:save', (_event, projectId: string, positions: Record<string, XYPosition>) =>
    saveLayout(projectId, positions)
  )
  ipcMain.handle('layout:clear', (_event, projectId: string) => clearLayout(projectId))

  ipcMain.handle('create:pick-folder', (event) =>
    openDialog(event, {
      title: 'Choose a folder of markdown files',
      buttonLabel: 'Use this folder',
      properties: ['openDirectory']
    })
  )
  ipcMain.handle('create:preview', (_event, folderPath: string) => run(() => inspectFolder(folderPath)))
  ipcMain.handle('create:upload', (_event, input: { name: string; folderPath: string }) =>
    run(() => uploadFolder(input))
  )

  ipcMain.handle('add:pick-file', async (event) => {
    const filePath = await openDialog(event, {
      title: 'Choose a document to add',
      buttonLabel: 'Choose',
      properties: ['openFile'],
      filters: MARKDOWN_FILTERS
    })
    return filePath ? inspectFile(filePath) : null
  })
  ipcMain.handle('add:suggest', (_event, input: { projectId: string; filePath: string }) =>
    run(() => suggestPlacement(input))
  )
  ipcMain.handle('add:place', (_event, input: PlacementInput) => run(() => placeFile(input)))

  ipcMain.handle('search:run', (_event, input: { projectId: string; query: string; limit?: number }) =>
    run(() => searchProject({ projectId: input.projectId, query: input.query, limit: input.limit ?? 8 }))
  )

  ipcMain.handle('tickets:members', () => run(listMembers))
  ipcMain.handle('tickets:sign-in', (_event, displayName: string) => run(() => signIn(displayName)))
  ipcMain.handle('tickets:me', () => run(currentMember))
  ipcMain.handle(
    'tickets:list',
    (
      _event,
      input: { scope?: 'mine' | 'project'; projectId?: string; status?: TicketStatus | null; limit?: number }
    ) => run(() => listTickets(input))
  )
  ipcMain.handle('tickets:create', (_event, input: TicketInput) => run(() => createTicket(input)))
  ipcMain.handle('tickets:get', (_event, ticketId: string, refresh: boolean) =>
    run(() => getTicket(ticketId, refresh))
  )
  ipcMain.handle('tickets:update', (_event, ticketId: string, patch: TicketPatch) =>
    run(() => updateTicket(ticketId, patch))
  )
  ipcMain.handle('tickets:status', (_event, ticketId: string, status: TicketStatus) =>
    run(() => setStatus(ticketId, status))
  )
  ipcMain.handle('tickets:files', (_event, ticketId: string, refresh: boolean) =>
    run(() => ticketFiles(ticketId, refresh))
  )
  ipcMain.handle(
    'tickets:attach',
    (_event, ticketId: string, fileId: string, source?: 'upload' | 'existing') =>
      run(() => attachFile(ticketId, fileId, source ?? 'existing'))
  )
  ipcMain.handle('tickets:detach', (_event, ticketId: string, fileId: string) =>
    run(() => detachFile(ticketId, fileId))
  )
  ipcMain.handle('tickets:comment', (_event, ticketId: string, body: string) =>
    run(() => addComment(ticketId, body))
  )
  ipcMain.handle(
    'tickets:activity',
    (_event, input: { projectId?: string; ticketId?: string; limit?: number }) =>
      run(() => listActivity(input))
  )
  ipcMain.handle('tickets:project-members', (_event, projectId: string) =>
    run(() => listProjectMembers(projectId))
  )
  ipcMain.handle('tickets:share', (_event, projectId: string, memberId: string) =>
    run(() => shareProject(projectId, memberId))
  )
  ipcMain.handle('tickets:unshare', (_event, projectId: string, memberId: string) =>
    run(() => unshareProject(projectId, memberId))
  )

  ipcMain.handle('shell:open-external', async (_event, url: string) => {
    await shell.openExternal(url)
  })
}
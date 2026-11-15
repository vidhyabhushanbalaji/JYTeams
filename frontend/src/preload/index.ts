/** The only bridge between the sandboxed renderer and the main process. */

import { contextBridge, ipcRenderer } from 'electron'

import type {
  AppConfig,
  FileContentInput,
  JyTeamsApi,
  PlacementInput,
  TicketInput,
  TicketPatch,
  TicketStatus,
  XYPosition
} from '../shared/types'

const api: JyTeamsApi = {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    set: (patch: Partial<AppConfig>) => ipcRenderer.invoke('config:set', patch)
  },
  health: {
    ping: () => ipcRenderer.invoke('health:ping')
  },
  projects: {
    list: () => ipcRenderer.invoke('projects:list'),
    get: (projectId: string) => ipcRenderer.invoke('projects:get', projectId),
    tree: (projectId: string, depth: number) => ipcRenderer.invoke('projects:tree', projectId, depth),
    directory: (directoryId: string) => ipcRenderer.invoke('projects:directory', directoryId),
    job: (jobId: string) => ipcRenderer.invoke('projects:job', jobId)
  },
  layout: {
    load: (projectId: string) => ipcRenderer.invoke('layout:load', projectId),
    save: (projectId: string, positions: Record<string, XYPosition>) =>
      ipcRenderer.invoke('layout:save', projectId, positions),
    clear: (projectId: string) => ipcRenderer.invoke('layout:clear', projectId)
  },
  files: {
    read: (fileId: string) => ipcRenderer.invoke('files:read', fileId),
    save: (input: FileContentInput) => ipcRenderer.invoke('files:save', input)
  },
  create: {
    pickFolder: () => ipcRenderer.invoke('create:pick-folder'),
    preview: (folderPath: string) => ipcRenderer.invoke('create:preview', folderPath),
    upload: (input: { name: string; folderPath: string }) => ipcRenderer.invoke('create:upload', input)
  },
  add: {
    pickFile: () => ipcRenderer.invoke('add:pick-file'),
    suggest: (input: { projectId: string; filePath: string; context?: string }) =>
      ipcRenderer.invoke('add:suggest', input),
    place: (input: PlacementInput) => ipcRenderer.invoke('add:place', input)
  },
  search: {
    run: (input: { projectId: string; query: string; limit?: number }) =>
      ipcRenderer.invoke('search:run', input)
  },
  tickets: {
    members: () => ipcRenderer.invoke('tickets:members'),
    signIn: (displayName: string) => ipcRenderer.invoke('tickets:sign-in', displayName),
    me: () => ipcRenderer.invoke('tickets:me'),
    list: (input) => ipcRenderer.invoke('tickets:list', input),
    create: (input: TicketInput) => ipcRenderer.invoke('tickets:create', input),
    get: (ticketId: string, refresh = false) => ipcRenderer.invoke('tickets:get', ticketId, refresh),
    update: (ticketId: string, patch: TicketPatch) => ipcRenderer.invoke('tickets:update', ticketId, patch),
    setStatus: (ticketId: string, status: TicketStatus) =>
      ipcRenderer.invoke('tickets:status', ticketId, status),
    files: (ticketId: string, refresh = false) =>
      ipcRenderer.invoke('tickets:files', ticketId, refresh),
    attach: (ticketId: string, fileId: string, source: 'upload' | 'existing' = 'existing') =>
      ipcRenderer.invoke('tickets:attach', ticketId, fileId, source),
    detach: (ticketId: string, fileId: string) => ipcRenderer.invoke('tickets:detach', ticketId, fileId),
    comment: (ticketId: string, body: string) => ipcRenderer.invoke('tickets:comment', ticketId, body),
    activity: (input) => ipcRenderer.invoke('tickets:activity', input),
    projectMembers: (projectId: string) => ipcRenderer.invoke('tickets:project-members', projectId),
    share: (projectId: string, memberId: string) => ipcRenderer.invoke('tickets:share', projectId, memberId),
    unshare: (projectId: string, memberId: string) =>
      ipcRenderer.invoke('tickets:unshare', projectId, memberId)
  },
  shell: {
    openExternal: (url: string) => ipcRenderer.invoke('shell:open-external', url)
  }
}

contextBridge.exposeInMainWorld('jyteams', api)
/** The only bridge between the sandboxed renderer and the main process. */

import { contextBridge, ipcRenderer } from 'electron'

import type { AppConfig, FileContentInput, JyTeamsApi, PlacementInput, XYPosition } from '../shared/types'

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
    suggest: (input: { projectId: string; filePath: string }) => ipcRenderer.invoke('add:suggest', input),
    place: (input: PlacementInput) => ipcRenderer.invoke('add:place', input)
  },
  search: {
    run: (input: { projectId: string; query: string; limit?: number }) =>
      ipcRenderer.invoke('search:run', input)
  },
  shell: {
    openExternal: (url: string) => ipcRenderer.invoke('shell:open-external', url)
  }
}

contextBridge.exposeInMainWorld('jyteams', api)
/** The Electron entry point: one window, one preload bridge, no remote content. */

import { app, BrowserWindow, shell } from 'electron'
import { join } from 'node:path'

import { registerIpc } from './ipc'
import { attachSmoke } from './smoke'

app.setName('JYTeams')
if (process.platform === 'win32') app.setAppUserModelId('com.jyteams.desktop')

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1320,
    height: 860,
    minWidth: 960,
    minHeight: 620,
    show: false,
    backgroundColor: '#ffffff',
    title: 'JYTeams',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  window.once('ready-to-show', () => window.show())

  // Development only: surface renderer errors in the terminal that started the app.
  if (!app.isPackaged) {
    window.webContents.on('console-message', (details) => {
      const record = details as unknown as { level?: string; message?: string }
      console.log(`[renderer] ${record.level ?? 'log'}: ${record.message ?? ''}`)
    })
    window.webContents.on('did-fail-load', (_event, code, description) => {
      console.error(`[renderer] failed to load: ${code} ${description}`)
    })
  }

  attachSmoke(window)

  window.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url)
    return { action: 'deny' }
  })

  const developmentUrl = process.env['ELECTRON_RENDERER_URL']
  if (developmentUrl) {
    void window.loadURL(developmentUrl)
  } else {
    void window.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

void app.whenReady().then(() => {
  registerIpc()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
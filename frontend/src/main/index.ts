/** The Electron entry point: one window, one preload bridge, no remote content. */

import { app, BrowserWindow, shell } from 'electron'
import { join } from 'node:path'

import { registerIpc } from './ipc'

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

  // JYTEAMS_SMOKE=1 opens the first project, reports what the canvas drew, then quits.
  if (process.env['JYTEAMS_SMOKE'] === '1') {
    window.webContents.on('did-finish-load', () => {
      setTimeout(() => {
        const script = `(async () => {
          const row = document.querySelector('.project-row')
          if (row) row.click()
          await new Promise((resolve) => setTimeout(resolve, 4500))
          const count = () => ({
            nodes: document.querySelectorAll('.react-flow__node').length,
            edges: document.querySelectorAll('.react-flow__edge').length,
            folders: document.querySelectorAll('.node--folder').length,
            files: document.querySelectorAll('.node--file').length
          })
          const before = count()
          const chevron = document.querySelector('.node--folder .node__chevron')
          if (chevron) chevron.click()
          await new Promise((resolve) => setTimeout(resolve, 1800))
          const after = count()
          const folder = document.querySelector('.node--folder')
          if (folder) folder.dispatchEvent(new MouseEvent('click', { bubbles: true }))
          await new Promise((resolve) => setTimeout(resolve, 400))

          // Drag the first card with a real pointer sequence (React Flow listens on
          // pointerdown, then window pointermove/up) and see whether it stayed put.
          const card = document.querySelector('.react-flow__node')
          const transformBefore = card ? card.style.transform : ''
          if (card) {
            const box = card.getBoundingClientRect()
            const base = {
              bubbles: true,
              cancelable: true,
              pointerId: 1,
              pointerType: 'mouse',
              isPrimary: true,
              button: 0,
              buttons: 1
            }
            card.dispatchEvent(
              new PointerEvent('pointerdown', { ...base, clientX: box.x + 24, clientY: box.y + 24 })
            )
            window.dispatchEvent(
              new PointerEvent('pointermove', { ...base, clientX: box.x + 150, clientY: box.y + 96 })
            )
            window.dispatchEvent(
              new PointerEvent('pointerup', {
                ...base,
                buttons: 0,
                clientX: box.x + 150,
                clientY: box.y + 96
              })
            )
            await new Promise((resolve) => setTimeout(resolve, 600))
          }
          const transformAfter = card ? card.style.transform : ''

          // The position store the drag writes through.
          const layoutKey = 'smoke-' + Date.now()
          await window.jyteams.layout.save(layoutKey, { 'dir:x': { x: 1, y: 2 } })
          const stored = await window.jyteams.layout.load(layoutKey)
          await window.jyteams.layout.clear(layoutKey)

          return {
            before,
            after,
            root: document.querySelector('.node--root .node__name')?.textContent ?? null,
            inspector: (document.querySelector('.workspace__side')?.innerText ?? '')
              .replace(/\\s+/g, ' ')
              .slice(0, 140),
            // Synthetic PointerEvents do not reliably start d3-drag, so report the wiring:
            // a card with the draggable class, plus a writable position store.
            dragReady: Boolean(document.querySelector('.react-flow__node.draggable')),
            pointerMoved: transformBefore !== transformAfter,
            layoutKeys: Object.keys(stored).length
          }
        })()`
        void window.webContents
          .executeJavaScript(script)
          .then((report: unknown) => {
            console.log('[smoke] ' + JSON.stringify(report))
          })
          .catch((error: unknown) => {
            console.error('[smoke] could not read the window', error)
          })
          .finally(() => app.quit())
      }, 3500)
    })
  }

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

/**
 * Development-only walkthrough: open the first project, read the tree, press a folder once
 * (select) and again (open), come back, and tidy - reporting what the window drew at each
 * step. Enabled with JYTEAMS_SMOKE=1; JYTEAMS_SMOKE_DIR saves a screenshot per step.
 *
 * It only clicks what a person would click, so it is safe to run any time.
 */

import { app, type BrowserWindow } from 'electron'
import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const REPORT = `(async () => {
  const cards = [...document.querySelectorAll('.react-flow__node')].map((element) => {
    const box = element.getBoundingClientRect()
    return {
      id: element.getAttribute('data-id'),
      x: box.x,
      y: box.y,
      width: box.width,
      height: box.height
    }
  })
  let overlaps = 0
  for (let i = 0; i < cards.length; i += 1) {
    for (let j = i + 1; j < cards.length; j += 1) {
      const a = cards[i]
      const b = cards[j]
      if (
        a.x < b.x + b.width &&
        a.x + a.width > b.x &&
        a.y < b.y + b.height &&
        a.y + a.height > b.y
      ) {
        overlaps += 1
      }
    }
  }
  const centreBox = document.querySelector('.node--centre')?.getBoundingClientRect() ?? null
  const aboveCentre = centreBox
    ? cards.filter((card) => card.id !== 'dir:root' && card.y + card.height > centreBox.top && card.y < centreBox.bottom).length
    : 0
  return {
    cards: cards.length,
    files: document.querySelectorAll('.node--file').length,
    folders: document.querySelectorAll('.node--folder').length,
    centre: document.querySelector('.node--centre .node__name')?.textContent ?? null,
    selected: document.querySelector('.node--folder.node--selected .node__name')?.textContent ?? null,
    title: document.querySelector('.workspace__side .side__body .side__title')?.textContent ?? null,
    backDisabled: document.querySelector('.topbar__back')?.disabled ?? null,
    crumbs: [...document.querySelectorAll('.crumb')]
      .map((element) => (element.textContent ?? '').trim())
      .join(' / '),
    overlaps,
    placed: cards.map((card) => [card.id.slice(0, 14), Math.round(card.x), Math.round(card.y)])
  }
})()`

export function attachSmoke(window: BrowserWindow): void {
  if (process.env['JYTEAMS_SMOKE'] !== '1') return
  window.webContents.once('did-finish-load', () => {
    void walk(window)
  })
}

async function walk(window: BrowserWindow): Promise<void> {
  const directory = process.env['JYTEAMS_SMOKE_DIR']
  const wait = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))
  const run = (code: string): Promise<unknown> => window.webContents.executeJavaScript(code)
  const shoot = async (name: string): Promise<void> => {
    if (!directory) return
    await mkdir(directory, { recursive: true })
    const image = await window.webContents.capturePage()
    await writeFile(join(directory, `${name}.png`), image.toPNG())
  }
  const report = async (label: string, shot: string): Promise<void> => {
    console.log(`[smoke] ${label} ` + JSON.stringify(await run(REPORT)))
    await shoot(shot)
  }

  try {
    await wait(2200)
    await run("document.querySelector('.project-row')?.click()")
    await wait(4200)
    await report('tree', '01-tree')

    await run(
      "document.querySelector('.node--folder')?.dispatchEvent(new MouseEvent('click', { bubbles: true }))"
    )
    await wait(1200)
    await report('selected', '02-selected')

    await run(
      "document.querySelector('.node--folder.node--selected')?.dispatchEvent(new MouseEvent('click', { bubbles: true }))"
    )
    await wait(2600)
    await report('opened', '03-opened')

    await run("document.querySelector('.topbar__back')?.click()")
    await wait(2200)
    await report('back', '04-back')

    await run(
      "[...document.querySelectorAll('button')].find((element) => (element.textContent ?? '').includes('Tidy'))?.click()"
    )
    await wait(1600)
    await report('tidy', '05-tidy')

    const layoutKeys = await run(`(async () => {
      const key = 'smoke-' + Date.now()
      await window.jyteams.layout.save(key, { 'dir:x': { x: 1, y: 2 } })
      const stored = await window.jyteams.layout.load(key)
      await window.jyteams.layout.clear(key)
      return Object.keys(stored).length
    })()`)
    console.log('[smoke] layoutKeys ' + JSON.stringify(layoutKeys))
  } catch (error) {
    console.error('[smoke] failed', error)
  } finally {
    app.quit()
  }
}
/**
 * A small markdown renderer for the document sheet.
 *
 * It builds React elements, never an HTML string: a document may contain `<script>` and that
 * has to appear as text. Hand-rolled on purpose - the desktop app has no markdown dependency,
 * and project documentation only needs headings, emphasis, code, lists, quotes, rules, links
 * and GFM tables.
 *
 * Deliberate limits: no nested lists, no images (a remote image would load outside the app's
 * fetch policy), and inline emphasis never spans a line break.
 */

import type { ReactNode } from 'react'

const FENCE = /^\s*(```|~~~)\s*([\w+-]*)\s*$/
const HEADING = /^(#{1,6})\s+(.*)$/
const RULE = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/
const QUOTE = /^\s*>\s?(.*)$/
const LIST = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/
const TABLE_SEPARATOR = /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/
const SAFE_SCHEME = /^(https?:|mailto:)/i
const MARKERS = ['`', '*', '_', '~', '[', '\\'] as const

type Block =
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'code'; language: string; text: string }
  | { kind: 'quote'; text: string }
  | { kind: 'list'; ordered: boolean; items: string[] }
  | { kind: 'table'; head: string[]; rows: string[][] }
  | { kind: 'rule' }

function nextMarker(text: string, from: number): number {
  let nearest = -1
  for (const marker of MARKERS) {
    const found = text.indexOf(marker, from)
    if (found !== -1 && (nearest === -1 || found < nearest)) nearest = found
  }
  return nearest
}

function isTableStart(line: string, next: string | undefined): boolean {
  return line.includes('|') && next !== undefined && TABLE_SEPARATOR.test(next)
}

function startsBlock(line: string, next: string | undefined): boolean {
  if (!line.trim()) return true
  if (FENCE.test(line) || HEADING.test(line) || RULE.test(line)) return true
  if (QUOTE.test(line) || LIST.test(line)) return true
  return isTableStart(line, next)
}

function splitRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '')
  return trimmed.split('|').map((cell) => cell.trim())
}

function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n?/g, '\n').split('\n')
  const blocks: Block[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]

    if (!line.trim()) {
      index += 1
      continue
    }

    const fence = FENCE.exec(line)
    if (fence) {
      const marker = fence[1]
      const body: string[] = []
      index += 1
      while (index < lines.length && !lines[index].trimStart().startsWith(marker)) {
        body.push(lines[index])
        index += 1
      }
      index += 1 // the closing fence (or the end of the document)
      blocks.push({ kind: 'code', language: fence[2] ?? '', text: body.join('\n') })
      continue
    }

    const heading = HEADING.exec(line)
    if (heading) {
      blocks.push({ kind: 'heading', level: heading[1].length, text: heading[2].trim() })
      index += 1
      continue
    }

    if (RULE.test(line)) {
      blocks.push({ kind: 'rule' })
      index += 1
      continue
    }

    if (QUOTE.test(line)) {
      const parts: string[] = []
      while (index < lines.length) {
        const match = QUOTE.exec(lines[index])
        if (!match) break
        parts.push(match[1].trim())
        index += 1
      }
      blocks.push({ kind: 'quote', text: parts.join(' ') })
      continue
    }

    const item = LIST.exec(line)
    if (item) {
      const ordered = /\d/.test(item[2])
      const items: string[] = []
      while (index < lines.length) {
        const match = LIST.exec(lines[index])
        if (!match) break
        items.push(match[3].trim())
        index += 1
      }
      blocks.push({ kind: 'list', ordered, items })
      continue
    }

    if (isTableStart(line, lines[index + 1])) {
      const head = splitRow(line)
      const rows: string[][] = []
      index += 2
      while (index < lines.length && lines[index].trim() && lines[index].includes('|')) {
        rows.push(splitRow(lines[index]))
        index += 1
      }
      blocks.push({ kind: 'table', head, rows })
      continue
    }

    const paragraph: string[] = []
    while (index < lines.length) {
      const current = lines[index]
      if (!current.trim()) break
      if (paragraph.length > 0 && startsBlock(current, lines[index + 1])) break
      paragraph.push(current.trim())
      index += 1
    }
    blocks.push({ kind: 'paragraph', text: paragraph.join(' ') })
  }

  return blocks
}

function InlineLink({ label, href }: { label: ReactNode; href: string }) {
  if (!SAFE_SCHEME.test(href)) return <>{label}</>
  return (
    <a
      className="md__link"
      href={href}
      rel="noreferrer"
      title={href}
      onClick={(event) => {
        event.preventDefault()
        void window.jyteams.shell.openExternal(href)
      }}
    >
      {label}
    </a>
  )
}

function renderInline(text: string, key: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let buffer = ''
  let index = 0
  let counter = 0

  const flush = (): void => {
    if (!buffer) return
    nodes.push(buffer)
    buffer = ''
  }

  while (index < text.length) {
    const marker = nextMarker(text, index)
    if (marker === -1) {
      buffer += text.slice(index)
      break
    }
    buffer += text.slice(index, marker)
    index = marker
    const rest = text.slice(index)

    const escaped = /^\\([\\`*_{}[\]()#+\-.!>~|])/.exec(rest)
    if (escaped) {
      buffer += escaped[1]
      index += escaped[0].length
      continue
    }

    const code = /^`([^`]+)`/.exec(rest)
    if (code) {
      flush()
      nodes.push(<code key={`${key}-code-${counter++}`}>{code[1]}</code>)
      index += code[0].length
      continue
    }

    const link = /^\[([^\]]+)\]\(([^)\s]+)\)/.exec(rest)
    if (link) {
      flush()
      const linkKey = `${key}-link-${counter++}`
      nodes.push(
        <InlineLink key={linkKey} label={renderInline(link[1], linkKey)} href={link[2]} />
      )
      index += link[0].length
      continue
    }

    const strong = /^(?:\*\*|__)(.+?)(?:\*\*|__)/.exec(rest)
    if (strong) {
      flush()
      const strongKey = `${key}-strong-${counter++}`
      nodes.push(<strong key={strongKey}>{renderInline(strong[1], strongKey)}</strong>)
      index += strong[0].length
      continue
    }

    const strike = /^~~(.+?)~~/.exec(rest)
    if (strike) {
      flush()
      const strikeKey = `${key}-del-${counter++}`
      nodes.push(<del key={strikeKey}>{renderInline(strike[1], strikeKey)}</del>)
      index += strike[0].length
      continue
    }

    const emphasis = /^(\*|_)([^*_\n]+?)\1/.exec(rest)
    if (emphasis) {
      const previous = index > 0 ? text[index - 1] : ' '
      const insideWord = emphasis[1] === '_' && /[A-Za-z0-9]/.test(previous)
      if (!insideWord) {
        flush()
        const emphasisKey = `${key}-em-${counter++}`
        nodes.push(<em key={emphasisKey}>{renderInline(emphasis[2], emphasisKey)}</em>)
        index += emphasis[0].length
        continue
      }
    }

    buffer += text[index]
    index += 1
  }

  flush()
  return nodes
}

function renderBlock(block: Block, index: number): ReactNode {
  const key = `block-${index}`

  switch (block.kind) {
    case 'heading': {
      const level = Math.min(block.level, 4)
      const Tag = `h${level}` as 'h1' | 'h2' | 'h3' | 'h4'
      return <Tag key={key}>{renderInline(block.text, key)}</Tag>
    }
    case 'paragraph':
      return <p key={key}>{renderInline(block.text, key)}</p>
    case 'code':
      return (
        <pre key={key} data-language={block.language || undefined}>
          <code>{block.text}</code>
        </pre>
      )
    case 'quote':
      return <blockquote key={key}>{renderInline(block.text, key)}</blockquote>
    case 'list': {
      const items = block.items.map((item, itemIndex) => {
        const itemKey = `${key}-item-${itemIndex}`
        return <li key={itemKey}>{renderInline(item, itemKey)}</li>
      })
      return block.ordered ? <ol key={key}>{items}</ol> : <ul key={key}>{items}</ul>
    }
    case 'table':
      return (
        <table key={key} className="md__table">
          <thead>
            <tr>
              {block.head.map((cell, columnIndex) => {
                const cellKey = `${key}-head-${columnIndex}`
                return <th key={cellKey}>{renderInline(cell, cellKey)}</th>
              })}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr key={`${key}-row-${rowIndex}`}>
                {block.head.map((_, columnIndex) => {
                  const cellKey = `${key}-row-${rowIndex}-${columnIndex}`
                  return <td key={cellKey}>{renderInline(row[columnIndex] ?? '', cellKey)}</td>
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )
    case 'rule':
      return <hr key={key} />
  }
}

export function Markdown({ text }: { text: string }) {
  return <>{parseBlocks(text).map(renderBlock)}</>
}

/** Word count for the sheet's footer (code blocks included, which is fine for a length hint). */
export function wordCount(text: string): number {
  const trimmed = text.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}

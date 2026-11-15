import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { Markdown, wordCount } from './markdown'

const render = (text: string): string => renderToStaticMarkup(createElement(Markdown, { text }))

describe('Markdown', () => {
  it('renders headings, paragraphs, emphasis, inline code and lists', () => {
    const markup = render('# Title\n\nSome **bold**, *italic* and `code`.\n\n- one\n- two')

    expect(markup).toContain('<h1>Title</h1>')
    expect(markup).toContain('<strong>bold</strong>')
    expect(markup).toContain('<em>italic</em>')
    expect(markup).toContain('<code>code</code>')
    expect(markup).toContain('<li>one</li>')
    expect(markup).toContain('<ul>')
  })

  it('renders a fenced block without interpreting its content', () => {
    const markup = render('```ts\nconst **x** = 1\n```')

    expect(markup).toContain('<pre')
    expect(markup).toContain('const **x** = 1')
    expect(markup).not.toContain('<strong>')
  })

  it('renders quotes, rules and GFM tables', () => {
    const markup = render('> a quote\n\n---\n\n| a | b |\n| --- | --- |\n| 1 | 2 |')

    expect(markup).toContain('<blockquote>a quote</blockquote>')
    expect(markup).toContain('<hr/>')
    expect(markup).toContain('<table class="md__table">')
    expect(markup).toContain('<th>a</th>')
    expect(markup).toContain('<td>1</td>')
  })

  it('keeps raw HTML as text instead of rendering it', () => {
    const markup = render('<script>alert(1)</script>')

    expect(markup).not.toContain('<script>')
    expect(markup).toContain('&lt;script&gt;')
  })

  it('links http(s) targets and refuses other schemes', () => {
    const safe = render('[docs](https://example.com/guide)')
    expect(safe).toContain('href="https://example.com/guide"')
    expect(safe).toContain('<a')

    const unsafe = render('[bad](javascript:alert)')
    expect(unsafe).not.toContain('javascript:')
    expect(unsafe).not.toContain('<a')
    expect(unsafe).toContain('bad')
  })

  it('does not turn snake_case text into emphasis', () => {
    expect(render('rollback_deployment_notes')).toContain('rollback_deployment_notes')
  })

  it('counts words for the footer', () => {
    expect(wordCount('  one two\nthree ')).toBe(3)
    expect(wordCount('')).toBe(0)
  })
})

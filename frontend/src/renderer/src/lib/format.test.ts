import { describe, expect, it } from 'vitest'

import { fileNameOf, humanBytes, plural, scoreText, shortDate } from './format'

describe('humanBytes', () => {
  it('formats bytes, kilobytes and megabytes', () => {
    expect(humanBytes(0)).toBe('0 B')
    expect(humanBytes(512)).toBe('512 B')
    expect(humanBytes(2048)).toBe('2.0 KB')
    expect(humanBytes(5 * 1024 * 1024)).toBe('5.0 MB')
  })

  it('survives nonsense input', () => {
    expect(humanBytes(Number.NaN)).toBe('0 B')
    expect(humanBytes(-4)).toBe('0 B')
  })
})

describe('plural', () => {
  it('switches on one', () => {
    expect(plural(1, 'file')).toBe('1 file')
    expect(plural(0, 'file')).toBe('0 files')
    expect(plural(3, 'directory', 'directories')).toBe('3 directories')
  })
})

describe('scoreText', () => {
  it('always shows two decimals', () => {
    expect(scoreText(0.9)).toBe('0.90')
    expect(scoreText(1)).toBe('1.00')
    expect(scoreText(Number.NaN)).toBe('0.00')
  })
})

describe('shortDate', () => {
  it('is blank for a missing or broken date', () => {
    expect(shortDate(null)).toBe('')
    expect(shortDate('not a date')).toBe('')
  })
})

describe('fileNameOf', () => {
  it('takes the last path segment', () => {
    expect(fileNameOf('docs/api/auth.md')).toBe('auth.md')
    expect(fileNameOf('README.md')).toBe('README.md')
  })
})
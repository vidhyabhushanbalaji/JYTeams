import { describe, expect, it } from 'vitest'

import type { CalendarItem } from '@shared/types'

import {
  addMonths,
  compareItems,
  dayMonthLabel,
  durationLabel,
  isOverdue,
  itemLabel,
  itemsByDay,
  monthRange,
  timeLabel
} from './calendar'

function item(overrides: Partial<CalendarItem>): CalendarItem {
  return {
    kind: 'event',
    id: 'e-1',
    title: 'Kickoff',
    day: '2026-03-03',
    project_id: 'p-1',
    project_name: 'Pulse',
    starts_at: '2026-03-03T10:00:00+00:00',
    ends_at: null,
    all_day: false,
    notes: '',
    editable: true,
    created_by: null,
    ticket_id: null,
    ticket_number: null,
    status: null,
    priority: null,
    assignee: null,
    mentions: [],
    ...overrides
  }
}

describe('monthRange', () => {
  it('starts on Monday and covers six weeks', () => {
    const range = monthRange(2026, 2, new Date(2026, 2, 15))

    expect(range.cells).toHaveLength(42)
    expect(range.weeks).toHaveLength(6)
    expect(range.from).toBe('2026-02-23')
    expect(range.to).toBe('2026-04-05')
  })

  it('marks the month and today', () => {
    const range = monthRange(2026, 2, new Date(2026, 2, 15))

    expect(range.cells.filter((cell) => cell.inMonth)).toHaveLength(31)
    expect(range.cells.find((cell) => cell.isToday)?.iso).toBe('2026-03-15')
  })

  it('moves between months across a year boundary', () => {
    expect(addMonths(2025, 11, 1)).toEqual({ year: 2026, month: 0 })
    expect(addMonths(2026, 0, -1)).toEqual({ year: 2025, month: 11 })
  })
})

describe('day buckets and labels', () => {
  it('groups items by day and orders events before deadlines', () => {
    const buckets = itemsByDay([
      item({ id: 'late', starts_at: '2026-03-03T15:00:00+00:00' }),
      item({ id: 'early', starts_at: '2026-03-03T08:00:00+00:00' }),
      item({ id: 'deadline', kind: 'deadline', starts_at: null, all_day: true, ticket_number: 12 })
    ])

    expect(buckets.get('2026-03-03')?.map((entry) => entry.id)).toEqual([
      'early',
      'late',
      'deadline'
    ])
  })

  it('sorts across days first', () => {
    const sorted = [item({ day: '2026-03-05' }), item({ day: '2026-03-01' })].sort(compareItems)

    expect(sorted[0].day).toBe('2026-03-01')
  })

  it('labels a time, a deadline and an overdue one', () => {
    expect(timeLabel(item({ starts_at: '2026-03-03T14:30:00' }))).toBe('14:30')
    expect(timeLabel(item({ all_day: true }))).toBe('All day')
    expect(itemLabel(item({ kind: 'deadline', ticket_number: 12, title: 'Fix it' }))).toBe(
      '#12 Fix it'
    )
    expect(isOverdue(item({ kind: 'deadline', day: '2026-03-01' }), '2026-03-02')).toBe(true)
    expect(
      isOverdue(item({ kind: 'deadline', day: '2026-03-01', status: 'done' }), '2026-03-02')
    ).toBe(false)
    expect(isOverdue(item({ day: '2026-03-01' }), '2026-03-02')).toBe(false)
  })

  it('describes a duration when there is one', () => {
    expect(
      durationLabel(
        item({ starts_at: '2026-03-03T10:00:00+00:00', ends_at: '2026-03-03T11:30:00+00:00' })
      )
    ).toBe('1h 30m')
    expect(durationLabel(item({ starts_at: '2026-03-03T10:00:00+00:00' }))).toBe('')
  })

  it('labels a calendar day without shifting it across timezones', () => {
    expect(dayMonthLabel('2026-03-20')).toMatch(/20/)
    expect(dayMonthLabel('not-a-day')).toBe('not-a-day')
  })
})

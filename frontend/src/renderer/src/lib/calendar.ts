/**
 * Pure helpers for the calendar page: the month grid, day buckets, ordering and labels.
 *
 * Days are `YYYY-MM-DD` strings (what the API speaks) and the grid starts on Monday, because the
 * rest of the app is written for a European working week.
 */

import type { CalendarItem } from '@shared/types'

export interface MonthCell {
  /** `YYYY-MM-DD`. */
  iso: string
  dayOfMonth: number
  /** False for the days borrowed from the neighbouring months to fill the grid. */
  inMonth: boolean
  isToday: boolean
}

export interface MonthRange {
  year: number
  /** 0-based, as `Date` uses. */
  month: number
  /** The grid's first and last day, so the request covers everything drawn. */
  from: string
  to: string
  cells: MonthCell[]
  weeks: MonthCell[][]
}

const pad = (value: number): string => `${value}`.padStart(2, '0')

export const isoDay = (value: Date): string =>
  `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`

export function addMonths(year: number, month: number, delta: number): { year: number; month: number } {
  const shifted = new Date(year, month + delta, 1)
  return { year: shifted.getFullYear(), month: shifted.getMonth() }
}

/** Six Monday-first weeks covering the month, plus the range to request. */
export function monthRange(year: number, month: number, today: Date = new Date()): MonthRange {
  const first = new Date(year, month, 1)
  const offset = (first.getDay() + 6) % 7
  const start = new Date(year, month, 1 - offset)
  const todayIso = isoDay(today)

  const cells: MonthCell[] = []
  for (let index = 0; index < 42; index += 1) {
    const date = new Date(start.getFullYear(), start.getMonth(), start.getDate() + index)
    const iso = isoDay(date)
    cells.push({
      iso,
      dayOfMonth: date.getDate(),
      inMonth: date.getMonth() === month,
      isToday: iso === todayIso
    })
  }

  const weeks: MonthCell[][] = []
  for (let index = 0; index < cells.length; index += 7) weeks.push(cells.slice(index, index + 7))

  return {
    year,
    month,
    from: cells[0].iso,
    to: cells[cells.length - 1].iso,
    cells,
    weeks
  }
}

export function itemsByDay(items: CalendarItem[]): Map<string, CalendarItem[]> {
  const buckets = new Map<string, CalendarItem[]>()
  for (const item of items) {
    const bucket = buckets.get(item.day)
    if (bucket) bucket.push(item)
    else buckets.set(item.day, [item])
  }
  for (const bucket of buckets.values()) bucket.sort(compareItems)
  return buckets
}

/** Events before deadlines on the same day, each timed item by its clock time. */
export function compareItems(left: CalendarItem, right: CalendarItem): number {
  if (left.day !== right.day) return left.day.localeCompare(right.day)
  if (left.kind !== right.kind) return left.kind === 'event' ? -1 : 1
  const leftTime = left.starts_at ? new Date(left.starts_at).getTime() : 0
  const rightTime = right.starts_at ? new Date(right.starts_at).getTime() : 0
  return leftTime - rightTime || left.title.localeCompare(right.title)
}

export const sortItems = (items: CalendarItem[]): CalendarItem[] => [...items].sort(compareItems)

/** `All day`, or the event's local start time. */
export function timeLabel(item: CalendarItem): string {
  if (item.all_day || !item.starts_at) return 'All day'
  const moment = new Date(item.starts_at)
  if (Number.isNaN(moment.getTime())) return 'All day'
  return `${pad(moment.getHours())}:${pad(moment.getMinutes())}`
}

/** A deadline that has passed while the ticket is still open. */
export function isOverdue(item: CalendarItem, today: string = isoDay(new Date())): boolean {
  return item.kind === 'deadline' && item.day < today && item.status !== 'done'
}

/**
 * `20 Mar` for a calendar day.
 *
 * The day is built from its parts rather than `new Date('2026-03-20')`, which JavaScript reads as
 * UTC midnight and would show as the previous day west of Greenwich.
 */
export function dayMonthLabel(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return iso
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short'
  })
}

/** How a chip reads: a deadline keeps its ticket number. */
export function itemLabel(item: CalendarItem): string {
  if (item.kind === 'deadline' && item.ticket_number !== null) {
    return `#${item.ticket_number} ${item.title}`
  }
  return item.title
}

/** A duration like `2h`, `45m`, or `All day` when the event has no end. */
export function durationLabel(item: CalendarItem): string {
  if (item.all_day || !item.starts_at || !item.ends_at) return ''
  const minutes = Math.round(
    (new Date(item.ends_at).getTime() - new Date(item.starts_at).getTime()) / 60_000
  )
  if (!Number.isFinite(minutes) || minutes <= 0) return ''
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours}h ${rest}m` : `${hours}h`
}

/** The month grid: six Monday-first weeks, each day carrying its chips. */

import type { CalendarItem } from '@shared/types'

import { isOverdue, itemLabel, itemsByDay, type MonthRange } from '../lib/calendar'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function CalendarMonth({
  grid,
  items,
  selectedDay,
  onSelectDay
}: {
  grid: MonthRange
  items: CalendarItem[]
  selectedDay: string
  onSelectDay: (day: string) => void
}) {
  const byDay = itemsByDay(items)

  return (
    <div className="cal">
      <div className="cal__weekdays" aria-hidden="true">
        {WEEKDAYS.map((label) => (
          <span key={label} className="cal__weekday">
            {label}
          </span>
        ))}
      </div>

      {grid.weeks.map((week) => (
        <div className="cal__week" key={week[0].iso}>
          {week.map((cell) => {
            const dayItems = byDay.get(cell.iso) ?? []
            const classes = [
              'cal__day',
              cell.inMonth ? '' : 'cal__day--outside',
              cell.isToday ? 'cal__day--today' : '',
              cell.iso === selectedDay ? 'cal__day--selected' : ''
            ]
              .filter(Boolean)
              .join(' ')

            return (
              <button
                key={cell.iso}
                type="button"
                className={classes}
                onClick={() => onSelectDay(cell.iso)}
                aria-label={`${cell.iso}, ${dayItems.length} item${dayItems.length === 1 ? '' : 's'}`}
                aria-pressed={cell.iso === selectedDay}
              >
                <span className="cal__day-number">{cell.dayOfMonth}</span>
                <span className="cal__chips">
                  {dayItems.slice(0, 3).map((item) => (
                    <span
                      key={`${item.kind}-${item.id}`}
                      className={`cal__chip cal__chip--${item.kind}${
                        isOverdue(item) ? ' cal__chip--overdue' : ''
                      }`}
                    >
                      {itemLabel(item)}
                    </span>
                  ))}
                  {dayItems.length > 3 ? (
                    <span className="cal__more">+{dayItems.length - 3} more</span>
                  ) : null}
                </span>
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}

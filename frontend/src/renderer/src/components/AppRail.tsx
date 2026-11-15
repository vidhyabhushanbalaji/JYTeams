import type { HealthReport } from '@shared/types'

import { initials } from '../lib/tickets'

export function AppRail({
  active,
  health,
  memberName,
  onHome,
  onTickets,
  onChat,
  onCalendar,
  onSettings,
  onSwitchUser
}: {
  active: 'home' | 'project' | 'tickets' | 'chat' | 'calendar'
  health: HealthReport | null
  memberName: string
  onHome: () => void
  onTickets: () => void
  onChat: () => void
  onCalendar: () => void
  onSettings: () => void
  onSwitchUser: () => void
}) {
  const apiUp = health?.api ?? false
  const supabaseUp = health?.supabase ?? false

  return (
    <nav className="rail" aria-label="Main">
      <div className="rail__mark" aria-hidden="true">
        JY
      </div>

      <button
        type="button"
        className={`rail__btn${active === 'home' ? ' rail__btn--active' : ''}`}
        onClick={onHome}
        aria-label="Projects"
        title="Projects"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <path d="M4 7.5A1.5 1.5 0 0 1 5.5 6h3.7l1.7 2h7.6A1.5 1.5 0 0 1 20 9.5v8a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5Z" />
        </svg>
      </button>

      <button
        type="button"
        className={`rail__btn${active === 'tickets' ? ' rail__btn--active' : ''}`}
        onClick={onTickets}
        aria-label="Tickets"
        title="Tickets"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h13A1.5 1.5 0 0 1 20 8.5v2a2 2 0 0 0 0 4v2a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 16.5v-2a2 2 0 0 0 0-4Z" />
          <path d="M9.5 11h6M9.5 14h4" />
        </svg>
      </button>

      <button
        type="button"
        className={`rail__btn${active === 'chat' ? ' rail__btn--active' : ''}`}
        onClick={onChat}
        aria-label="Chat"
        title="Chat"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <path d="M4.5 6.5A1.5 1.5 0 0 1 6 5h12a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 18 16H9l-4.5 3.5Z" />
          <path d="M8 9.5h8M8 12.5h5" />
        </svg>
      </button>

      <button
        type="button"
        className={`rail__btn${active === 'calendar' ? ' rail__btn--active' : ''}`}
        onClick={onCalendar}
        aria-label="Calendar"
        title="Calendar"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <rect x="4" y="5.5" width="16" height="14" rx="1.5" />
          <path d="M4 10h16M8.5 4v3M15.5 4v3M8.5 14h3M8.5 17h6" />
        </svg>
      </button>

      <div className="rail__spacer" />

      <div
        className="rail__status"
        title={health ? `API: ${health.apiDetail}` : 'Checking the backend'}
      >
        <span className={`dot${apiUp ? ' dot--on' : ''}`} />
        <span>API</span>
      </div>
      <div className="rail__status" title={health?.supabaseDetail ?? 'Supabase not checked'}>
        <span className={`dot${supabaseUp ? ' dot--on' : apiUp ? ' dot--warn' : ''}`} />
        <span>DB</span>
      </div>

      <button
        type="button"
        className="rail__user"
        onClick={onSwitchUser}
        aria-label="Switch user"
        title={memberName ? `Signed in as ${memberName} — switch user` : 'Switch user'}
      >
        <span className="avatar avatar--sm">{initials(memberName)}</span>
      </button>

      <button
        type="button"
        className="rail__btn"
        onClick={onSettings}
        aria-label="Settings"
        title="Settings"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <circle cx="12" cy="12" r="3.1" />
          <path d="M12 4.2v1.6M12 18.2v1.6M4.2 12h1.6M18.2 12h1.6M6.5 6.5l1.1 1.1M16.4 16.4l1.1 1.1M17.5 6.5l-1.1 1.1M7.6 16.4l-1.1 1.1" />
        </svg>
      </button>
    </nav>
  )
}
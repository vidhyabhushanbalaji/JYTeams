import type { HealthReport } from '@shared/types'

export function AppRail({
  active,
  health,
  onHome,
  onSettings
}: {
  active: 'home' | 'project'
  health: HealthReport | null
  onHome: () => void
  onSettings: () => void
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
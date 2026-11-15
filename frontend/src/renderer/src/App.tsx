import { useCallback, useEffect, useState } from 'react'

import type { AppConfig, HealthReport } from '@shared/types'

import type { TicketFocus } from './lib/ticketFocus'
import { AppRail } from './components/AppRail'
import { HomeScreen } from './components/HomeScreen'
import { IdentityGate } from './components/IdentityGate'
import { ProjectScreen } from './components/ProjectScreen'
import { SettingsDialog } from './components/SettingsDialog'
import { TicketsScreen } from './components/TicketsScreen'
import { Toasts } from './components/Toasts'
import { useIdentity } from './state/useIdentity'
import { useToasts } from './state/useToasts'

type View =
  | { kind: 'home' }
  | { kind: 'project'; projectId: string; focus: TicketFocus | null }
  | { kind: 'tickets' }

export default function App() {
  const [view, setView] = useState<View>({ kind: 'home' })
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [health, setHealth] = useState<HealthReport | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { toasts, notify, dismiss } = useToasts()
  const identity = useIdentity()

  useEffect(() => {
    document.body.dataset.platform = navigator.userAgent.includes('Mac') ? 'mac' : 'other'
  }, [])

  const loadConfig = useCallback(async () => {
    setConfig(await window.jyteams.config.get())
  }, [])

  const refreshHealth = useCallback(async () => {
    setHealth(await window.jyteams.health.ping())
  }, [])

  useEffect(() => {
    void loadConfig()
    void refreshHealth()
  }, [loadConfig, refreshHealth])

  const switchUser = useCallback(() => {
    setView({ kind: 'home' })
    void identity.signOut()
  }, [identity])

  if (identity.status !== 'ready' || !identity.member) {
    return (
      <>
        <IdentityGate
          members={identity.members}
          loading={identity.status === 'loading'}
          error={identity.error}
          onPick={async (displayName) => (await identity.signIn(displayName)).ok}
          onRetry={() => void identity.reload()}
          onOpenSettings={() => setSettingsOpen(true)}
        />
        <SettingsDialog
          open={settingsOpen}
          config={config}
          health={health}
          onClose={() => setSettingsOpen(false)}
          onSaved={async () => {
            await loadConfig()
            await refreshHealth()
            await identity.reload()
          }}
        />
        <Toasts toasts={toasts} onDismiss={dismiss} />
      </>
    )
  }

  const member = identity.member

  return (
    <div className="app-shell">
      <AppRail
        active={view.kind}
        health={health}
        memberName={member.display_name}
        onHome={() => setView({ kind: 'home' })}
        onTickets={() => setView({ kind: 'tickets' })}
        onSettings={() => setSettingsOpen(true)}
        onSwitchUser={switchUser}
      />

      <div className="app-body">
        {view.kind === 'home' ? (
          <HomeScreen
            onOpenProject={(projectId) => setView({ kind: 'project', projectId, focus: null })}
            onOpenSettings={() => setSettingsOpen(true)}
            notify={notify}
          />
        ) : view.kind === 'tickets' ? (
          <TicketsScreen
            member={member}
            members={identity.members}
            onOpenProject={(projectId, focus) => setView({ kind: 'project', projectId, focus })}
            onSwitchUser={switchUser}
            notify={notify}
          />
        ) : (
          <ProjectScreen
            key={view.projectId}
            projectId={view.projectId}
            member={member}
            members={identity.members}
            ticketFocus={view.focus}
            onClearTicketFocus={() =>
              setView({ kind: 'project', projectId: view.projectId, focus: null })
            }
            onOpenSettings={() => setSettingsOpen(true)}
            notify={notify}
          />
        )}
      </div>

      <SettingsDialog
        open={settingsOpen}
        config={config}
        health={health}
        onClose={() => setSettingsOpen(false)}
        onSaved={async () => {
          await loadConfig()
          await refreshHealth()
          await identity.reload()
        }}
      />

      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  )
}
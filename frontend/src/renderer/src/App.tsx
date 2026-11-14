import { useCallback, useEffect, useState } from 'react'

import type { AppConfig, HealthReport } from '@shared/types'

import { AppRail } from './components/AppRail'
import { HomeScreen } from './components/HomeScreen'
import { ProjectScreen } from './components/ProjectScreen'
import { SettingsDialog } from './components/SettingsDialog'
import { Toasts } from './components/Toasts'
import { useToasts } from './state/useToasts'

type View = { kind: 'home' } | { kind: 'project'; projectId: string }

export default function App() {
  const [view, setView] = useState<View>({ kind: 'home' })
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [health, setHealth] = useState<HealthReport | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { toasts, notify, dismiss } = useToasts()

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

  return (
    <div className="app-shell">
      <AppRail
        active={view.kind}
        health={health}
        onHome={() => setView({ kind: 'home' })}
        onSettings={() => setSettingsOpen(true)}
      />

      <div className="app-body">
        {view.kind === 'home' ? (
          <HomeScreen
            onOpenProject={(projectId) => setView({ kind: 'project', projectId })}
            onOpenSettings={() => setSettingsOpen(true)}
            notify={notify}
          />
        ) : (
          <ProjectScreen
            key={view.projectId}
            projectId={view.projectId}

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
        }}
      />

      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  )
}
import { useEffect, useState } from 'react'

import type { AppConfig, HealthReport } from '@shared/types'

import { Dialog, Field, Spinner } from './primitives'

export function SettingsDialog({
  open,
  config,
  health,
  onClose,
  onSaved
}: {
  open: boolean
  config: AppConfig | null
  health: HealthReport | null
  onClose: () => void
  onSaved: () => Promise<void>
}) {
  const [baseUrl, setBaseUrl] = useState('')
  const [devUserId, setDevUserId] = useState('')
  const [bearerToken, setBearerToken] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setBaseUrl(config?.baseUrl ?? '')
    setDevUserId(config?.devUserId ?? '')
    setBearerToken(config?.bearerToken ?? '')
  }, [open, config])

  const save = async (): Promise<void> => {
    setSaving(true)
    await window.jyteams.config.set({ baseUrl, devUserId, bearerToken })
    await onSaved()
    setSaving(false)
    onClose()
  }

  return (
    <Dialog
      open={open}
      title="Settings"
      subtitle="Where the backend lives, and who the app says it is."
      onClose={onClose}
      footer={
        <>
          <span className="spacer" />
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn btn--primary" onClick={() => void save()} disabled={saving}>
            {saving ? <Spinner label="Saving" /> : null}
            Save and check
          </button>
        </>
      }
    >
      <Field label="Backend address" hint="The FastAPI service, usually on port 8000.">
        <input
          className="field__input"
          value={baseUrl}
          onChange={(event) => setBaseUrl(event.target.value)}
          placeholder="http://127.0.0.1:8000"
          spellCheck={false}
        />
      </Field>

      <Field
        label="Dev user id"
        hint="Only used when the backend runs with AUTH_MODE=dev. Leave it blank to let the backend use its own DEV_USER_ID."
      >
        <input
          className="field__input"
          value={devUserId}
          onChange={(event) => setDevUserId(event.target.value)}
          placeholder="00000000-0000-0000-0000-000000000000"
          spellCheck={false}
        />
      </Field>

      <Field
        label="Bearer token"
        hint="Only for AUTH_MODE=supabase. When set it takes priority over the dev user id."
      >
        <input
          className="field__input"
          value={bearerToken}
          onChange={(event) => setBearerToken(event.target.value)}
          placeholder="Paste a Supabase access token"
          spellCheck={false}
        />
      </Field>

      <div className="kv">
        <div className="kv__row">
          <span className="kv__key">API</span>
          <span className="kv__value">{health ? (health.api ? 'reachable' : health.apiDetail) : 'not checked'}</span>
        </div>
        <div className="kv__row">
          <span className="kv__key">Supabase</span>
          <span className="kv__value">
            {health ? (health.supabase ? 'configured' : health.supabaseDetail) : 'not checked'}
          </span>
        </div>
      </div>

      <p className="side__empty">
        These values are stored in the app's user data folder, never in the repository. The backend
        keeps its own secrets in <span className="mono">backend/.env</span>.
      </p>
    </Dialog>
  )
}
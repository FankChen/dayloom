import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  CalendarDays,
  BookOpen,
  Download,
  FileUp,
  KeyRound,
  Languages,
  Leaf,
  Plug,
  Save,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { api, saveAccessToken } from '../api'
import { Modal, PageHeader } from '../components/ui'
import { ModelSettings } from '../components/ModelSettings'
import { AccountSettings } from '../components/AccountSettings'
import { MailSettings } from '../components/MailSettings'
import { DeviceSettings } from '../components/DeviceSettings'
import { LanguagePicker } from '../components/LanguagePicker'
import type { Preferences } from '../types'
import { useWorkspace } from '../useWorkspace'

function PlanningSettings({ preferences }: { preferences: Preferences }) {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const [draft, setDraft] = useState(preferences)
  return (
    <form
      className="settings-form"
      onSubmit={(event) => {
        event.preventDefault()
        void execute(() => api('/api/settings', 'PUT', draft), 'Planning preferences saved.')
      }}
    >
      <div className="form-grid">
        <label>
          {t('Timezone')}
          <select
            value={draft.timezone}
            onChange={(event) => setDraft({ ...draft, timezone: event.target.value })}
          >
            {Array.from(new Set([draft.timezone, ...Intl.supportedValuesOf('timeZone')])).map(
              (zone) => (
                <option key={zone}>{zone}</option>
              ),
            )}
          </select>
        </label>
        <label>
          {t('Daily focus capacity (minutes)')}
          <input
            type="number"
            min={15}
            max={720}
            step={15}
            required
            value={draft.daily_minutes}
            onChange={(event) => setDraft({ ...draft, daily_minutes: Number(event.target.value) })}
          />
        </label>
      </div>
      <div className="form-grid">
        <label>
          {t('Day begins')}
          <select
            value={draft.work_start}
            onChange={(event) => setDraft({ ...draft, work_start: Number(event.target.value) })}
          >
            {Array.from({ length: 23 }, (_, hour) => (
              <option key={hour} value={hour}>
                {String(hour).padStart(2, '0')}:00
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('Day ends')}
          <select
            value={draft.work_end}
            onChange={(event) => setDraft({ ...draft, work_end: Number(event.target.value) })}
          >
            {Array.from({ length: 23 }, (_, offset) => offset + 1).map((hour) => (
              <option key={hour} value={hour}>
                {String(hour).padStart(2, '0')}:00
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="range-label">
        {t('Daily priorities')} <output>{draft.focus_count}</output>
        <input
          type="range"
          min={1}
          max={5}
          value={draft.focus_count}
          onChange={(event) => setDraft({ ...draft, focus_count: Number(event.target.value) })}
        />
      </label>
      <div>
        <button className="button" type="submit" disabled={busy}>
          <Save size={15} />
          {t('Save preferences')}
        </button>
      </div>
    </form>
  )
}

export function SettingsPage() {
  const { t } = useTranslation()
  const { data, busy, execute, refresh } = useWorkspace()
  const client = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [token, setToken] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [confirmation, setConfirmation] = useState('')
  if (!data) return null
  const { settings, calendar } = data
  const sources = [...new Set(calendar.map((event) => event.source))]
  async function importCalendar(file: File) {
    await execute(async () => {
      if (file.size > 500000) throw new Error('Calendar files must be smaller than 500 KB.')
      return api('/api/calendar/import', 'POST', {
        content: await file.text(),
        source: file.name.slice(0, 100),
      })
    }, 'Calendar imported. Your plan has been updated.')
  }
  return (
    <>
      <PageHeader title={t('On your terms.')} eyebrow={t('WORKSPACE SETTINGS')}>
        <span className="subtle-label">
          <ShieldCheck size={14} />
          {t(data.account.mode === 'oidc' ? 'Private account' : 'Local workspace')}
        </span>
      </PageHeader>
      <section className="settings-section">
        <div className="settings-section-title">
          <Languages size={19} />
          <div>
            <h2>{t('Language')}</h2>
            <span>{t('Display preferences')}</span>
          </div>
        </div>
        <div className="settings-body">
          <LanguagePicker />
          <Link to="/guide" className="button secondary guide-settings-link">
            <BookOpen size={16} />
            {t('Open the getting-started guide')}
          </Link>
        </div>
      </section>
      <AccountSettings />
      <MailSettings />
      <DeviceSettings />
      <section className="settings-section">
        <div className="settings-section-title">
          <Leaf size={19} />
          <div>
            <h2>{t('Your daily rhythm')}</h2>
            <span>{t('Time & capacity')}</span>
          </div>
        </div>
        <PlanningSettings preferences={settings.preferences} />
      </section>
      <section className="settings-section">
        <div className="settings-section-title">
          <Plug size={19} />
          <div>
            <h2>{t('Connections')}</h2>
            <span>{t('Models & calendar')}</span>
          </div>
        </div>
        <div className="settings-body">
          <ModelSettings />
          <div className="connection-row">
            <span className="connection-icon">
              <CalendarDays size={20} />
            </span>
            <div>
              <strong>{t('Calendar snapshots')}</strong>
              <span>
                {calendar.length
                  ? t('{{count}} events / {{sources}}', {
                      count: calendar.length,
                      sources: sources.join(', '),
                    })
                  : t('No calendar imported')}
              </span>
            </div>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => fileInput.current?.click()}
            >
              <FileUp size={15} />
              {t('Import .ics')}
            </button>
            <input
              ref={fileInput}
              hidden
              type="file"
              accept=".ics,text/calendar"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void importCalendar(file)
                event.target.value = ''
              }}
            />
          </div>
          {calendar.length > 0 && (
            <button
              className="text-button text-coral"
              disabled={busy}
              onClick={() =>
                void execute(() => api('/api/calendar', 'DELETE'), 'Calendar data removed.')
              }
            >
              <Trash2 size={13} />
              {t('Remove imported calendars')}
            </button>
          )}
          <div className="connection-row worker-status">
            <span className={`connection-dot ${settings.worker_online ? 'online' : ''}`} />
            <strong>
              {settings.worker_online
                ? t('Background worker connected')
                : t('Background worker offline')}
            </strong>
          </div>
        </div>
      </section>
      <section className="settings-section">
        <div className="settings-section-title">
          <ShieldCheck size={19} />
          <div>
            <h2>{t('Access & data')}</h2>
            <span>{t('Your private workspace')}</span>
          </div>
        </div>
        <div className="settings-body">
          {data.account.mode === 'local' && (
            <form
              className="access-form"
              onSubmit={(event) => {
                event.preventDefault()
                saveAccessToken(token)
                setToken('')
                client.removeQueries({ queryKey: ['workspace'] })
                refresh()
              }}
            >
              <label>
                {t('Workspace access token')}
                <input
                  type="password"
                  autoComplete="off"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
              </label>
              <button type="submit" className="button secondary">
                <KeyRound size={15} />
                {t('Update access')}
              </button>
            </form>
          )}
          <div className="data-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                void execute(async () => {
                  const exported = await api('/api/data')
                  const url = URL.createObjectURL(
                    new Blob([JSON.stringify(exported, null, 2)], { type: 'application/json' }),
                  )
                  const link = document.createElement('a')
                  link.href = url
                  link.download = 'dayloom-export.json'
                  link.click()
                  URL.revokeObjectURL(url)
                }, 'Workspace exported.')
              }
            >
              <Download size={15} />
              {t('Export workspace')}
            </button>
            <button
              className="button secondary"
              disabled={
                busy ||
                data.tasks.length > 0 ||
                data.memories.length > 0 ||
                data.messages.length > 0 ||
                data.actions.length > 0 ||
                data.calendar.length > 0
              }
              onClick={() =>
                void execute(() => api('/api/demo', 'POST'), 'Sample workspace loaded.')
              }
            >
              {t('Load sample workspace')}
            </button>
          </div>
          <div className="danger-zone">
            <div>
              <strong>{t('Delete workspace data')}</strong>
              <p>
                {t(
                  'Tasks, chats, memories, calendar imports and execution history. Server credentials and external-provider copies are not included.',
                )}
              </p>
            </div>
            <button
              className="button secondary danger-outline"
              onClick={() => {
                setConfirmation('')
                setDeleting(true)
              }}
            >
              <Trash2 size={15} />
              {t('Delete data')}
            </button>
          </div>
        </div>
      </section>
      {deleting && (
        <Modal title={t('Delete all workspace data?')} onClose={() => setDeleting(false)}>
          <form
            onSubmit={async (event) => {
              event.preventDefault()
              if (confirmation !== 'DELETE') return
              if (
                await execute(
                  () =>
                    api('/api/data', 'DELETE', undefined, {
                      'X-Dayloom-Confirm': 'DELETE MY DATA',
                    }),
                  'Workspace data deleted.',
                )
              )
                setDeleting(false)
            }}
          >
            <label>
              {t('Type DELETE to confirm')}
              <input
                autoFocus
                value={confirmation}
                onChange={(event) => setConfirmation(event.target.value)}
                required
                pattern="DELETE"
              />
            </label>
            <div className="form-actions">
              <button className="button secondary" type="button" onClick={() => setDeleting(false)}>
                {t('Cancel')}
              </button>
              <button
                className="button danger"
                type="submit"
                disabled={busy || confirmation !== 'DELETE'}
              >
                {t('Delete permanently')}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  )
}

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Globe, Plus, Save, Trash2 } from 'lucide-react'
import { api } from '../api'
import { isNative, NativeBridge } from '../platform/native'
import { useWorkspace } from '../useWorkspace'

export function DeviceSettings() {
  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const status = useQuery({
    queryKey: ['device-permissions'],
    queryFn: () => NativeBridge.notificationStatus(),
    enabled: isNative,
    refetchInterval: 10000,
  })
  const sources = useQuery({
    queryKey: ['notification-sources'],
    queryFn: () => NativeBridge.notificationSources(),
    enabled: Boolean(isNative && status.data?.supported && status.data.granted),
    refetchInterval: 10000,
  })
  const captured = useQuery({
    queryKey: ['local-notifications'],
    queryFn: () => NativeBridge.readNotifications(),
    enabled: Boolean(isNative && status.data?.supported && status.data.granted),
    refetchInterval: 10000,
  })
  const [selected, setSelected] = useState<string[] | null>(null)
  const [url, setUrl] = useState('')
  const browser = useQuery({
    queryKey: ['browser-configuration'],
    queryFn: () => api<{ enabled: boolean; allowed_origins: string[] }>('/api/browser/config'),
  })
  const packages = selected ?? status.data?.packages ?? []
  const sourceNames = Array.from(
    new Set([...(sources.data?.sources.map((source) => source.packageName) ?? []), ...packages]),
  )
  async function configure(enabled: boolean) {
    await NativeBridge.configureNotifications({ enabled, packages })
    setSelected(null)
    await client.invalidateQueries({ queryKey: ['device-permissions'] })
    await client.invalidateQueries({ queryKey: ['local-notifications'] })
  }
  return (
    <>
      {isNative && (
        <section className="settings-section">
          <div className="settings-section-title">
            <Bell size={19} />
            <div>
              <h2>Device notifications</h2>
              <span>Encrypted local capture / 24-hour retention</span>
            </div>
          </div>
          <div className="settings-body">
            {status.error && <p role="alert">{status.error.message}</p>}
            {status.data && !status.data.supported && (
              <p className="muted">Cross-app notification access is unavailable on iOS.</p>
            )}
            {status.data?.supported && (
              <>
                <button
                  className="button secondary"
                  onClick={() => void execute(() => NativeBridge.openNotificationAccess())}
                >
                  <Bell size={15} />
                  System notification access
                </button>
                <label className="consent">
                  <input
                    type="checkbox"
                    disabled={!status.data.granted || busy}
                    checked={status.data.enabled}
                    onChange={(event) =>
                      void execute(
                        () => configure(event.target.checked),
                        'Capture settings updated.',
                      )
                    }
                  />
                  <span>Capture selected apps on this device only</span>
                </label>
                <div className="notification-sources">
                  {sourceNames.map((name) => (
                    <label className="consent" key={name}>
                      <input
                        type="checkbox"
                        checked={packages.includes(name)}
                        onChange={(event) =>
                          setSelected(
                            event.target.checked
                              ? [...packages, name]
                              : packages.filter((item) => item !== name),
                          )
                        }
                      />
                      <span>{name}</span>
                    </label>
                  ))}
                </div>
                <div className="data-actions">
                  <button
                    className="button secondary"
                    disabled={busy || selected === null}
                    onClick={() =>
                      void execute(
                        () => configure(status.data!.enabled),
                        'Notification sources saved.',
                      )
                    }
                  >
                    <Save size={15} />
                    Save sources
                  </button>
                  <button
                    className="button secondary"
                    disabled={busy}
                    onClick={() =>
                      void execute(async () => {
                        await NativeBridge.clearNotifications()
                        await client.invalidateQueries({ queryKey: ['local-notifications'] })
                      }, 'Local notifications cleared.')
                    }
                  >
                    <Trash2 size={15} />
                    Clear local capture
                  </button>
                </div>
                {captured.data?.events.map((notification) => (
                  <div className="connection-row" key={notification.id}>
                    <div>
                      <strong>{notification.title || notification.packageName}</strong>
                      <span>{notification.packageName}</span>
                      <p>{notification.body}</p>
                    </div>
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        void execute(
                          () =>
                            api('/api/tasks', 'POST', {
                              title: notification.title || 'Captured notification',
                              notes: `${notification.packageName}\n${notification.body}`,
                            }),
                          'Selected notification uploaded as a task.',
                        )
                      }
                    >
                      <Plus size={15} />
                      Upload as task
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        </section>
      )}
      <section className="settings-section">
        <div className="settings-section-title">
          <Globe size={19} />
          <div>
            <h2>Isolated browser</h2>
            <span>
              {browser.data?.enabled ? 'Public page reading available' : 'Runner not configured'}
            </span>
          </div>
        </div>
        <div className="settings-body">
          {browser.error && <p role="alert">{browser.error.message}</p>}
          {browser.data?.enabled && (
            <form
              onSubmit={async (event) => {
                event.preventDefault()
                if (
                  await execute(
                    () => api('/api/actions', 'POST', { tool: 'ReadWebPage', payload: { url } }),
                    'Webpage read ready for approval.',
                  )
                )
                  setUrl('')
              }}
            >
              <label>
                Approved HTTPS webpage
                <input
                  type="url"
                  required
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                />
              </label>
              <button className="button secondary" disabled={busy} type="submit">
                <Globe size={15} />
                Prepare page read
              </button>
            </form>
          )}
        </div>
      </section>
    </>
  )
}

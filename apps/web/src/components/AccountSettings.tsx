import { useQuery, useQueryClient } from '@tanstack/react-query'
import { LogOut, Monitor, ShieldCheck, Trash2 } from 'lucide-react'
import { api, saveAccessToken } from '../api'
import { clearNativeSession } from '../platform/native'
import { useWorkspace } from '../useWorkspace'

interface DeviceSession {
  id: string
  device: string
  created_at: string
  current: boolean
}

export function AccountSettings() {
  const { data, busy, execute } = useWorkspace()
  const client = useQueryClient()
  const devices = useQuery({
    queryKey: ['account-sessions'],
    queryFn: () => api<DeviceSession[]>('/api/auth/sessions'),
    enabled: data?.account.mode === 'oidc',
  })
  if (!data || data.account.mode !== 'oidc') return null
  return (
    <section className="settings-section">
      <div className="settings-section-title">
        <ShieldCheck size={19} />
        <div>
          <h2>Your account</h2>
          <span>{data.account.name}</span>
        </div>
      </div>
      <div className="settings-body">
        {devices.error && <p role="alert">{devices.error.message}</p>}
        {devices.data?.map((device) => (
          <div className="connection-row" key={device.id}>
            <span className="connection-icon">
              <Monitor size={19} />
            </span>
            <div>
              <strong>{device.current ? 'This session' : 'Signed-in device'}</strong>
              <span>{device.device}</span>
            </div>
            {!device.current && (
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  void execute(async () => {
                    await api(`/api/auth/sessions/${device.id}`, 'DELETE')
                    await client.invalidateQueries({ queryKey: ['account-sessions'] })
                  }, 'Session revoked.')
                }
              >
                <Trash2 size={15} />
                Revoke
              </button>
            )}
          </div>
        ))}
        <button
          className="button secondary"
          disabled={busy}
          onClick={() =>
            void execute(async () => {
              try {
                await api('/api/auth/logout', 'POST')
              } finally {
                await clearNativeSession()
                saveAccessToken('')
                client.clear()
                window.location.replace('/today')
              }
            })
          }
        >
          <LogOut size={15} />
          Sign out
        </button>
      </div>
    </section>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { MonitorSmartphone, Pencil, Plug, Plus, Save, Trash2 } from 'lucide-react'
import { api } from '../api'
import type { DeviceCatalog, DeviceConnection } from '../types'
import { useWorkspace } from '../useWorkspace'
import { ConfirmDelete, IconButton, Modal } from './ui'

export function DeviceConnections() {
  const { t } = useTranslation()
  const { data, busy, execute } = useWorkspace()
  const query = useQuery({
    queryKey: ['agent', data?.account.workspace_id, 'devices'],
    queryFn: () => api<DeviceCatalog>('/api/devices'),
  })
  const [editing, setEditing] = useState(false)
  const [current, setCurrent] = useState<DeviceConnection | null>(null)
  const [discovering, setDiscovering] = useState<DeviceConnection | null>(null)
  const [removing, setRemoving] = useState<DeviceConnection | null>(null)
  const [consent, setConsent] = useState(false)
  const [draft, setDraft] = useState({ label: '', endpoint: '', token: '', tools: [] as string[] })
  function closeEditor() {
    setEditing(false)
    setDraft((previous) => ({ ...previous, token: '' }))
    setCurrent(null)
  }
  return (
    <section className="agent-devices">
      <div className="section-heading">
        <h2>
          <MonitorSmartphone size={20} />
          {t('Connected device services')}
        </h2>
        <button
          className="button secondary"
          disabled={!query.data || busy || !query.data.allowed_servers.length}
          onClick={() => {
            setCurrent(null)
            setDraft({
              label: '',
              endpoint: query.data?.allowed_servers[0] ?? '',
              token: '',
              tools: [],
            })
            setEditing(true)
          }}
        >
          <Plus size={16} />
          {t('Connect device service')}
        </button>
      </div>
      {query.error && (
        <p role="alert" className="inline-error">
          {t(query.error.message)}
        </p>
      )}
      <p className="field-help">
        {t(
          'Tools run on the device hosting the connected service, not automatically on the device displaying this page. Phone control requires a compatible service and system permissions.',
        )}
      </p>
      {!query.data?.allowed_servers.length && (
        <p className="agent-run-warning">
          {t(
            'Device connections are not enabled on this server yet. Ask the deployer to add a trusted MCP service address.',
          )}
        </p>
      )}
      {query.data?.connections.map((connection) => (
        <article className="agent-device-row" key={connection.id}>
          <MonitorSmartphone size={24} />
          <div>
            <h3>{connection.label}</h3>
            <p>{connection.endpoint}</p>
            <span>
              {t('{{count}} authorized tools', { count: connection.authorized_tools.length })}
            </span>
          </div>
          <div className="agent-device-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => {
                setDiscovering(connection)
                setConsent(false)
              }}
            >
              <Plug size={15} />
              {t('Discover device tools')}
            </button>
            <IconButton
              icon={Pencil}
              label={t('Edit {{title}}', { title: connection.label })}
              onClick={() => {
                setCurrent(connection)
                setDraft({
                  label: connection.label,
                  endpoint: connection.endpoint,
                  token: '',
                  tools: connection.authorized_tools,
                })
                setEditing(true)
              }}
            />
            <IconButton
              icon={Trash2}
              label={t('Disconnect {{name}}', { name: connection.label })}
              onClick={() => setRemoving(connection)}
            />
          </div>
        </article>
      ))}
      {editing && (
        <Modal
          title={t(current ? 'Edit device service' : 'Connect device service')}
          onClose={closeEditor}
        >
          <form
            onSubmit={async (event) => {
              event.preventDefault()
              if (
                await execute(
                  () =>
                    api(
                      current ? `/api/devices/${current.id}` : '/api/devices',
                      current ? 'PUT' : 'POST',
                      { ...draft, token: draft.token || null, version: current?.version ?? 0 },
                    ),
                  'Device connection saved.',
                )
              )
                closeEditor()
            }}
          >
            <label>
              {t('Device service name')}
              <input
                required
                maxLength={100}
                value={draft.label}
                onChange={(event) => setDraft({ ...draft, label: event.target.value })}
              />
            </label>
            <label>
              {t('Approved MCP service address')}
              <select
                required
                value={draft.endpoint}
                onChange={(event) =>
                  setDraft({ ...draft, endpoint: event.target.value, token: '', tools: [] })
                }
              >
                {query.data?.allowed_servers.map((endpoint) => (
                  <option key={endpoint}>{endpoint}</option>
                ))}
              </select>
            </label>
            <label>
              {t('Device access token')}
              <input
                type="password"
                autoComplete="new-password"
                maxLength={4096}
                required={!!current && current.endpoint !== draft.endpoint}
                value={draft.token}
                onChange={(event) => setDraft({ ...draft, token: event.target.value })}
                placeholder={current ? t('Leave blank to keep the saved token') : undefined}
              />
            </label>
            <p className="field-help">
              {t(
                'Saving stores the connection securely without contacting the device. Discovery reads its tools; you choose which tools to authorize afterward.',
              )}
            </p>
            {current && current.endpoint === draft.endpoint && (
              <fieldset className="agent-device-permissions">
                <legend>{t('Authorized device tools')}</legend>
                {current.catalog.map((tool) => (
                  <label key={tool.name}>
                    <input
                      type="checkbox"
                      checked={draft.tools.includes(tool.name)}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          tools: event.target.checked
                            ? [...draft.tools, tool.name]
                            : draft.tools.filter((name) => name !== tool.name),
                        })
                      }
                    />
                    <span>
                      <strong>{tool.name}</strong>
                      <small>{tool.description}</small>
                    </span>
                  </label>
                ))}
              </fieldset>
            )}
            <div className="form-actions">
              <button className="button secondary" type="button" onClick={closeEditor}>
                {t('Cancel')}
              </button>
              <button className="button" disabled={busy}>
                <Save size={16} />
                {t('Save connection')}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {discovering && (
        <Modal title={t('Discover device tools')} onClose={() => setDiscovering(null)}>
          <p>{discovering.label}</p>
          <p className="field-help">
            {t(
              'Discovery contacts this device using its saved token and clears previous tool permissions. It does not run device actions.',
            )}
          </p>
          <label className="consent">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>{t('Allow this device connection and tool discovery.')}</span>
          </label>
          <div className="form-actions">
            <button className="button secondary" onClick={() => setDiscovering(null)}>
              {t('Cancel')}
            </button>
            <button
              className="button"
              disabled={busy || !consent}
              onClick={async () => {
                if (
                  await execute(async () => {
                    const saved = await api<DeviceConnection>(
                      `/api/devices/${discovering.id}/discover`,
                      'POST',
                      { version: discovering.version, allow_external: consent },
                    )
                    setCurrent(saved)
                    setDraft({ label: saved.label, endpoint: saved.endpoint, token: '', tools: [] })
                    setEditing(true)
                  }, 'Device tools discovered. Select the tools you trust.')
                )
                  setDiscovering(null)
              }}
            >
              <Plug size={16} />
              {t('Discover device tools')}
            </button>
          </div>
        </Modal>
      )}
      {removing && (
        <ConfirmDelete
          title={t('Disconnect this device service?')}
          busy={busy}
          onClose={() => setRemoving(null)}
          onConfirm={() =>
            void execute(
              () => api(`/api/devices/${removing.id}`, 'DELETE'),
              'Device disconnected.',
            ).then((success) => {
              if (success) setRemoving(null)
            })
          }
        />
      )}
    </section>
  )
}

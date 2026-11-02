import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Plug, Save, Trash2 } from 'lucide-react'
import { api } from '../api'
import type { Settings } from '../types'
import { useWorkspace } from '../useWorkspace'
import { ConfirmDelete, Modal } from './ui'

interface Configuration {
  connection: Settings['provider']
  allowed_origins: string[]
  providers: { name: string; label: string }[]
}

function ModelEditor({
  configuration,
  onClose,
}: {
  configuration: Configuration
  onClose: () => void
}) {
  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const current = configuration.connection
  const [draft, setDraft] = useState({
    provider: current.managed === 'workspace' && current.name ? current.name : 'OpenAIProvider',
    base_url: current.base_url ?? 'https://api.openai.com/v1',
    model: current.model ?? '',
    api_key: '',
    max_tokens: current.max_tokens ?? 2400,
    daily_limit: current.daily_limit ?? 100,
    version: current.version ?? 0,
  })
  return (
    <Modal title="Model connection" onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          if (await execute(() => api('/api/models', 'PUT', draft), 'Model connection saved.')) {
            setDraft({ ...draft, api_key: '' })
            await client.invalidateQueries({ queryKey: ['model-configuration'] })
            onClose()
          }
        }}
      >
        <label>
          Provider
          <select
            value={draft.provider}
            onChange={(event) => setDraft({ ...draft, provider: event.target.value })}
          >
            {configuration.providers.map((provider) => (
              <option key={provider.name} value={provider.name}>
                {provider.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          API base URL
          <input
            type="url"
            required
            value={draft.base_url}
            onChange={(event) => setDraft({ ...draft, base_url: event.target.value })}
          />
        </label>
        <label>
          Model
          <input
            required
            maxLength={200}
            value={draft.model}
            placeholder="gpt-4.1-mini"
            onChange={(event) => setDraft({ ...draft, model: event.target.value })}
          />
        </label>
        <label>
          API key
          <input
            type="password"
            autoComplete="off"
            required
            maxLength={4096}
            value={draft.api_key}
            onChange={(event) => setDraft({ ...draft, api_key: event.target.value })}
          />
        </label>
        <div className="form-grid">
          <label>
            Output token limit
            <input
              type="number"
              min={128}
              max={8192}
              required
              value={draft.max_tokens}
              onChange={(event) => setDraft({ ...draft, max_tokens: Number(event.target.value) })}
            />
          </label>
          <label>
            Daily request limit
            <input
              type="number"
              min={1}
              max={1000}
              required
              value={draft.daily_limit}
              onChange={(event) => setDraft({ ...draft, daily_limit: Number(event.target.value) })}
            />
          </label>
        </div>
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="button" disabled={busy}>
            <Save size={15} />
            Save connection
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function ModelSettings() {
  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const configuration = useQuery({
    queryKey: ['model-configuration'],
    queryFn: () => api<Configuration>('/api/models'),
  })
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState(false)
  if (configuration.isPending) return <p role="status">Loading model connection...</p>
  if (!configuration.data)
    return <p role="alert">{configuration.error?.message ?? 'Model settings unavailable.'}</p>
  const model = configuration.data.connection
  return (
    <>
      <div className="connection-row">
        <span className="connection-icon">
          <KeyRound size={20} />
        </span>
        <div>
          <strong>{model.model ?? model.label}</strong>
          <span>
            {model.managed === 'workspace' && model.configured
              ? `${model.used_today ?? 0} / ${model.daily_limit} requests today`
              : model.configured
                ? model.label
                : 'Not connected'}
          </span>
        </div>
        <button className="button secondary" onClick={() => setEditing(true)}>
          <KeyRound size={15} />
          {model.managed === 'workspace' && model.configured ? 'Edit model' : 'Connect model'}
        </button>
      </div>
      {model.managed === 'workspace' && model.configured && (
        <div className="data-actions">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() =>
              void execute(async () => {
                await api('/api/models/test', 'POST')
                await client.invalidateQueries({ queryKey: ['model-configuration'] })
              }, 'Model connection verified.')
            }
          >
            <Plug size={15} />
            Test connection
          </button>
          <button
            className="button secondary danger-outline"
            disabled={busy}
            onClick={() => setRemoving(true)}
          >
            <Trash2 size={15} />
            Disconnect model
          </button>
        </div>
      )}
      {editing && (
        <ModelEditor configuration={configuration.data} onClose={() => setEditing(false)} />
      )}
      {removing && (
        <ConfirmDelete
          title="Disconnect this model?"
          busy={busy}
          onClose={() => setRemoving(false)}
          onConfirm={() => {
            void execute(async () => {
              await api('/api/models', 'DELETE')
              await client.invalidateQueries({ queryKey: ['model-configuration'] })
            }, 'Model disconnected.').then((success) => {
              if (success) setRemoving(false)
            })
          }}
        />
      )}
    </>
  )
}

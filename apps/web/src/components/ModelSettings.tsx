import { useTranslation } from 'react-i18next'
import { useId, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, KeyRound, Plug, Save, Trash2 } from 'lucide-react'
import { api } from '../api'
import type { Settings } from '../types'
import { useWorkspace } from '../useWorkspace'
import { ConfirmDelete, Modal } from './ui'

export interface ModelConfiguration {
  connection: Settings['provider']
  allowed_origins: string[]
  providers: { name: string; label: string }[]
}

const servicePresets = [
  {
    label: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4.1-mini',
    consoleUrl: 'https://platform.openai.com/api-keys',
  },
  {
    label: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
    consoleUrl: 'https://platform.deepseek.com/api_keys',
  },
  {
    label: 'Google Gemini',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
    model: 'gemini-2.5-flash',
    consoleUrl: 'https://aistudio.google.com/apikey',
  },
]

export function ModelConnectionForm({
  configuration,
  onSaved,
  onCancel,
  guided = false,
}: {
  configuration: ModelConfiguration
  onSaved: (connection: Settings['provider']) => void
  onCancel?: () => void
  guided?: boolean
}) {
  const { t } = useTranslation()
  const fieldId = useId()
  const [saveError, setSaveError] = useState('')
  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const current = configuration.connection
  const [draft, setDraft] = useState({
    provider: current.managed === 'workspace' && current.name ? current.name : 'OpenAIProvider',
    base_url:
      current.base_url ??
      (configuration.allowed_origins.includes('https://api.openai.com')
        ? 'https://api.openai.com/v1'
        : ''),
    model: current.model ?? '',
    api_key: '',
    max_tokens: current.max_tokens ?? 2400,
    daily_limit: current.daily_limit ?? 100,
    version: current.version ?? 0,
  })
  const presets = servicePresets.filter(
    (preset) =>
      configuration.allowed_origins.includes(new URL(preset.baseUrl).origin) &&
      configuration.providers.some((provider) => provider.name === 'OpenAIProvider'),
  )
  const selectedPreset = presets.find((preset) => preset.baseUrl === draft.base_url)
  return (
    <form
      className="model-form"
      onSubmit={async (event) => {
        event.preventDefault()
        setSaveError('')
        await execute(async () => {
          try {
            const saved = await api<Settings['provider']>('/api/models', 'PUT', draft)
            setDraft({ ...draft, api_key: '' })
            await client.invalidateQueries({ queryKey: ['model-configuration'] })
            onSaved(saved)
          } catch (error) {
            setSaveError(error instanceof Error ? error.message : 'Model settings unavailable.')
            throw error
          }
        }, 'Model connection saved.')
      }}
    >
      {guided && (
        <div className="preset-field">
          <label htmlFor={`${fieldId}-service`}>{t('API service')}</label>
          <select
            id={`${fieldId}-service`}
            value={selectedPreset?.baseUrl ?? ''}
            onChange={(event) => {
              const preset = presets.find((candidate) => candidate.baseUrl === event.target.value)
              setDraft({
                ...draft,
                base_url: preset?.baseUrl ?? '',
                model: preset?.model ?? '',
                api_key: '',
                provider: preset ? 'OpenAIProvider' : draft.provider,
              })
            }}
          >
            <option value="">{t('Custom service')}</option>
            {presets.map((preset) => (
              <option key={preset.baseUrl} value={preset.baseUrl}>
                {preset.label}
              </option>
            ))}
          </select>
          <p className="field-help">
            {t(
              'Presets fill editable examples, not a guarantee of availability. Confirm the model ID in your provider account.',
            )}
          </p>
          {selectedPreset && (
            <a
              className="text-button provider-console"
              href={selectedPreset.consoleUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink size={14} />
              {t('Open {{provider}} API key console', { provider: selectedPreset.label })}
            </a>
          )}
        </div>
      )}
      <label>
        {t('Provider')}
        <select
          value={draft.provider}
          onChange={(event) => setDraft({ ...draft, provider: event.target.value })}
        >
          {configuration.providers.map((provider) => (
            <option key={provider.name} value={provider.name}>
              {t(provider.label)}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t('API base URL')}
        <input
          type="url"
          required
          aria-describedby={guided ? `${fieldId}-endpoint` : undefined}
          value={draft.base_url}
          onChange={(event) => setDraft({ ...draft, base_url: event.target.value, api_key: '' })}
        />
      </label>
      {guided && (
        <div className="field-help" id={`${fieldId}-endpoint`}>
          <p>
            {t(
              'Use the API base address from your provider, usually ending in /v1. Do not paste a chat website or a /chat/completions endpoint.',
            )}
          </p>
          <p>
            {t('Allowed service origins:')}{' '}
            <span className="allowed-origins">{configuration.allowed_origins.join(', ')}</span>
          </p>
          <details>
            <summary>{t('My provider is not listed')}</summary>
            <p>
              {t(
                'Your server administrator must add the HTTPS origin to DAYLOOM_MODEL_ALLOWED_ORIGINS before you can connect it. This guide does not bypass that restriction.',
              )}
            </p>
          </details>
        </div>
      )}
      <label>
        {t('Model')}
        <input
          required
          maxLength={200}
          aria-describedby={guided ? `${fieldId}-model` : undefined}
          value={draft.model}
          placeholder={t('gpt-4.1-mini')}
          onChange={(event) => setDraft({ ...draft, model: event.target.value })}
        />
      </label>
      {guided && (
        <p className="field-help" id={`${fieldId}-model`}>
          {t(
            'Copy a model ID available to your API account. A chat subscription does not necessarily include API credit.',
          )}
        </p>
      )}
      <label>
        {t('API key')}
        <input
          type="password"
          autoComplete="off"
          required
          maxLength={4096}
          aria-describedby={guided ? `${fieldId}-key` : undefined}
          value={draft.api_key}
          onChange={(event) => setDraft({ ...draft, api_key: event.target.value })}
        />
      </label>
      {guided && (
        <p className="field-help" id={`${fieldId}-key`}>
          {t(
            'Create an API key in your provider console and paste it here. It is encrypted on your Dayloom server, never added to chat or saved in tutorial progress.',
          )}
        </p>
      )}
      <div className="form-grid">
        <label>
          {t('Output token limit')}
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
          {t('Daily request limit')}
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
      {guided && (
        <p className="field-help">
          {t(
            'These limits cap requests and output length, not money spent. Saving the connection does not make a model request.',
          )}
        </p>
      )}
      {saveError && (
        <p className="inline-error" role="alert">
          {t(saveError)}
        </p>
      )}
      <div className="form-actions">
        {onCancel && (
          <button type="button" className="button secondary" onClick={onCancel}>
            {t('Cancel')}
          </button>
        )}
        <button type="submit" className="button" disabled={busy}>
          <Save size={15} />
          {t('Save connection')}
        </button>
      </div>
    </form>
  )
}

export function ModelSettings() {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const configuration = useQuery({
    queryKey: ['model-configuration'],
    queryFn: () => api<ModelConfiguration>('/api/models'),
  })
  const [editing, setEditing] = useState(false)
  const [removing, setRemoving] = useState(false)
  if (configuration.isPending) return <p role="status">{t('Loading model connection...')}</p>
  if (!configuration.data)
    return <p role="alert">{t(configuration.error?.message ?? 'Model settings unavailable.')}</p>
  const model = configuration.data.connection
  return (
    <>
      <div className="connection-row">
        <span className="connection-icon">
          <KeyRound size={20} />
        </span>
        <div>
          <strong>
            {model.configured ? (model.model ?? t(model.label)) : t('Model not connected')}
          </strong>
          <span>
            {model.managed === 'workspace' && model.configured
              ? t('{{used}} / {{limit}} requests today', {
                  used: model.used_today ?? 0,
                  limit: model.daily_limit,
                })
              : model.configured
                ? t(model.label)
                : t('Not connected')}
          </span>
        </div>
        <button className="button secondary" onClick={() => setEditing(true)}>
          <KeyRound size={15} />
          {model.managed === 'workspace' && model.configured ? t('Edit model') : t('Connect model')}
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
            {t('Test connection')}
          </button>
          <button
            className="button secondary danger-outline"
            disabled={busy}
            onClick={() => setRemoving(true)}
          >
            <Trash2 size={15} />
            {t('Disconnect model')}
          </button>
        </div>
      )}
      {editing && (
        <Modal title={t('Model connection')} onClose={() => setEditing(false)}>
          <ModelConnectionForm
            configuration={configuration.data}
            onSaved={() => setEditing(false)}
            onCancel={() => setEditing(false)}
          />
        </Modal>
      )}
      {removing && (
        <ConfirmDelete
          title={t('Disconnect this model?')}
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

import { useTranslation } from 'react-i18next'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Clock3, Pause, ShieldCheck } from 'lucide-react'
import { api, formatDateTime } from '../api'
import type { Action } from '../types'
import { useWorkspace } from '../useWorkspace'
import { Modal } from './ui'

function localDateTime(milliseconds: number) {
  const date = new Date(milliseconds)
  return new Date(milliseconds - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

interface ScheduleRequest {
  action_id: string
  action_digest: string
  name: string
  starts_at: string
  expires_at: string
  interval_seconds: number
  max_runs: number
}

export function ScheduleDialog({ action, onClose }: { action: Action; onClose: () => void }) {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const [name, setName] = useState(String(action.payload.subject ?? action.tool))
  const [start, setStart] = useState(() => localDateTime(Date.now() + 300000))
  const [expiry, setExpiry] = useState(() => localDateTime(Date.now() + 7 * 86400000))
  const [minutes, setMinutes] = useState(1440)
  const [runs, setRuns] = useState(1)
  const [review, setReview] = useState<{ request: ScheduleRequest; digest: string } | null>(null)
  return (
    <Modal title={t('Authorize schedule')} onClose={onClose}>
      <form
        onChange={() => setReview(null)}
        onSubmit={async (event) => {
          event.preventDefault()
          if (review) {
            if (
              await execute(async () => {
                await api('/api/automations', 'POST', {
                  ...review.request,
                  approval_digest: review.digest,
                })
                await client.invalidateQueries({ queryKey: ['automations'] })
              }, 'Schedule authorized.')
            )
              onClose()
          } else {
            const request = {
              action_id: action.id,
              action_digest: action.digest,
              name,
              starts_at: new Date(start).toISOString(),
              expires_at: new Date(expiry).toISOString(),
              interval_seconds: minutes * 60,
              max_runs: runs,
            }
            await execute(async () => {
              const result = await api<{ approval_digest: string }>(
                '/api/automations/preview',
                'POST',
                request,
              )
              setReview({ request, digest: result.approval_digest })
            })
          }
        }}
      >
        <label>
          {t('Name')}
          <input
            required
            maxLength={200}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label>
          {t('First run (')}
          {Intl.DateTimeFormat().resolvedOptions().timeZone})
          <input
            type="datetime-local"
            required
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </label>
        <div className="form-grid">
          <label>
            {t('Interval (minutes)')}
            <input
              type="number"
              min={1}
              max={10080}
              required
              value={minutes}
              onChange={(event) => setMinutes(Number(event.target.value))}
            />
          </label>
          <label>
            {t('Maximum runs')}
            <input
              type="number"
              min={1}
              max={100}
              required
              value={runs}
              onChange={(event) => setRuns(Number(event.target.value))}
            />
          </label>
        </div>
        <label>
          {t('Authorization expires')}
          <input
            type="datetime-local"
            required
            value={expiry}
            onChange={(event) => setExpiry(event.target.value)}
          />
        </label>
        <pre className="payload-preview">{JSON.stringify(action.payload, null, 2)}</pre>
        {review && (
          <p className="approval-note">
            {t('This exact content may execute up to')} {runs}
            {t('times without another approval, until the authorization expires.')}
          </p>
        )}
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button type="submit" className="button" disabled={busy}>
            <ShieldCheck size={15} />
            {review ? t('Authorize schedule') : t('Review schedule')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function OutcomeDialog({ action, onClose }: { action: Action; onClose: () => void }) {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const [outcome, setOutcome] = useState('')
  const [evidence, setEvidence] = useState('')
  return (
    <Modal title={t('Record checked outcome')} onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          if (
            await execute(
              () => api(`/api/actions/${action.id}/resolve`, 'POST', { outcome, evidence }),
              'Owner-reported outcome recorded.',
            )
          )
            onClose()
        }}
      >
        <label>
          {t('Provider outcome')}
          <select required value={outcome} onChange={(event) => setOutcome(event.target.value)}>
            <option value="">{t('Select checked outcome')}</option>
            <option value="confirmed_sent">{t('Confirmed accepted by provider')}</option>
            <option value="confirmed_not_sent">{t('Confirmed not accepted by provider')}</option>
          </select>
        </label>
        <label>
          {t('Evidence or provider reference')}
          <textarea
            required
            minLength={10}
            maxLength={2000}
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
          />
        </label>
        <p className="approval-note">
          {t('Owner-reported outcome; not independent provider verification.')}
        </p>
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button className="button" type="submit" disabled={busy}>
            {t('Record outcome')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

interface Automation {
  id: string
  name: string
  active: number
  runs_created: number
  max_runs: number
  next_run_at: number
  expires_at: number
}

export function AutomationList() {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const rules = useQuery({
    queryKey: ['automations'],
    queryFn: async () =>
      (await api<Automation[]>('/api/automations')).map((rule) => ({
        ...rule,
        expired: rule.expires_at * 1000 <= Date.now(),
      })),
    refetchInterval: 5000,
  })
  if (!rules.data?.length) return rules.error ? <p role="alert">{rules.error.message}</p> : null
  return (
    <section className="automation-section">
      <div className="section-heading">
        <h2>{t('Scheduled automations')}</h2>
        <Clock3 size={17} />
      </div>
      {rules.data.map((rule) => (
        <div className="connection-row" key={rule.id}>
          <span className="connection-icon">
            <Clock3 size={18} />
          </span>
          <div>
            <strong>{rule.name}</strong>
            <span>
              {!rule.active
                ? t('Paused')
                : rule.runs_created >= rule.max_runs
                  ? t('Run limit reached')
                  : rule.expired
                    ? t('Authorization expired')
                    : formatDateTime(rule.next_run_at * 1000)}{' '}
              / {rule.runs_created} {t('of')} {rule.max_runs}
              {t('runs')}
            </span>
          </div>
          {Boolean(rule.active) && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() =>
                void execute(async () => {
                  await api(`/api/automations/${rule.id}/pause`, 'POST')
                  await client.invalidateQueries({ queryKey: ['automations'] })
                }, 'Automation paused.')
              }
            >
              <Pause size={15} />
              {t('Pause')}
            </button>
          )}
        </div>
      ))}
    </section>
  )
}

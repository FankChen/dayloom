import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CircleCheck,
  KeyRound,
  LoaderCircle,
  MessageSquare,
  Plug,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { ActionCard } from '../components/ActionCard'
import { LanguagePicker } from '../components/LanguagePicker'
import { ModelConnectionForm, type ModelConfiguration } from '../components/ModelSettings'
import { PageHeader } from '../components/ui'
import { readGuideProgress, saveGuideProgress } from '../guideProgress'
import type { Action, Message } from '../types'
import { useWorkspace } from '../useWorkspace'

const steps = [
  'Meet Dayloom',
  'Connect your API',
  'Verify connection',
  'Try a conversation',
  'Review and begin',
]

export function GuideWelcome() {
  const { t } = useTranslation()
  const { data } = useWorkspace()
  const [saved] = useState(() => (data ? readGuideProgress(data.account.workspace_id) : null))
  if (!data || data.settings.provider.configured) return null
  return (
    <section className="getting-started-banner" aria-label={t('Get started')}>
      <BookOpen size={24} />
      <div>
        <h2>{t('Your workspace is ready.')}</h2>
        <p>
          {t(
            'Start with your tasks and daily plan. Connect a model when you are ready for AI assistance.',
          )}
        </p>
      </div>
      <Link to="/guide" className="button">
        {t(saved ? 'Continue setup' : 'Connect a model')}
        <ArrowRight size={16} />
      </Link>
    </section>
  )
}

export function Guide() {
  const { t } = useTranslation()
  const { data, busy, execute } = useWorkspace()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [progress, setProgress] = useState(() => {
    const saved = data ? readGuideProgress(data.account.workspace_id) : null
    return saved?.completed
      ? { step: 0, completed: false }
      : (saved ?? { step: 0, completed: false })
  })
  const [storageAvailable, setStorageAvailable] = useState(true)
  const [verifiedFor, setVerifiedFor] = useState('')
  const [testConsent, setTestConsent] = useState(false)
  const [chatConsent, setChatConsent] = useState(false)
  const [draftMessage, setDraftMessage] = useState<string | null>(null)
  const [failure, setFailure] = useState('')
  const [reply, setReply] = useState<{ message: Message; actions: Action[] } | null>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const configuration = useQuery({
    queryKey: ['model-configuration'],
    queryFn: () => api<ModelConfiguration>('/api/models'),
  })
  const connection = configuration.data?.connection
  const fingerprint = connection?.configured
    ? JSON.stringify([
        connection.name,
        connection.base_url,
        connection.model,
        connection.version,
        connection.managed,
      ])
    : ''
  const verified = Boolean(fingerprint && verifiedFor === fingerprint)
  const activeStep =
    progress.step >= 3 && !verified ? 2 : progress.step === 4 && !reply ? 3 : progress.step
  const ready = Boolean(data)
  useEffect(() => {
    if (!ready) return
    headingRef.current?.focus({ preventScroll: true })
    if (activeStep > 0) headingRef.current?.scrollIntoView({ block: 'start' })
  }, [activeStep, ready])
  if (!data) return null
  const message =
    draftMessage ??
    t(
      "Create a 30-minute task to organize tomorrow's priorities. Do not send email or perform any external action.",
    )
  function moveTo(step: number, completed = false) {
    const next = { step, completed }
    setProgress(next)
    setFailure('')
    setStorageAvailable(saveGuideProgress(data!.account.workspace_id, next))
  }
  async function perform(operation: () => Promise<void>) {
    setFailure('')
    return execute(async () => {
      try {
        await operation()
      } catch (error) {
        setFailure(error instanceof Error ? error.message : 'Something went wrong.')
        throw error
      }
    })
  }
  return (
    <div className="guide-page">
      <PageHeader title={t('Make Dayloom yours.')} eyebrow={t('GETTING STARTED')}>
        <LanguagePicker />
      </PageHeader>
      <div className="guide-layout">
        <ol className="guide-steps" aria-label={t('Setup progress')}>
          {steps.map((label, index) => (
            <li key={label} aria-current={index === activeStep ? 'step' : undefined}>
              <button
                type="button"
                disabled={busy || index > activeStep}
                onClick={() => moveTo(index)}
              >
                <span className={`guide-step-number ${index < activeStep ? 'complete' : ''}`}>
                  {index < activeStep ? <Check size={16} /> : index + 1}
                </span>
                <span>{t(label)}</span>
              </button>
            </li>
          ))}
        </ol>
        <section className="guide-body" aria-labelledby="guide-step-heading">
          <div className="guide-step-heading">
            <p className="eyebrow">
              {t('Step {{current}} of {{total}}', { current: activeStep + 1, total: steps.length })}
            </p>
            <h2 ref={headingRef} id="guide-step-heading" tabIndex={-1}>
              {t(steps[activeStep])}
            </h2>
          </div>
          {!storageAvailable && (
            <p className="inline-error" role="status">
              {t(
                'Browser storage is unavailable. You can continue, but your place may not survive a reload.',
              )}
            </p>
          )}
          {activeStep === 0 && (
            <div className="guide-intro">
              <p className="guide-lead">
                {t(
                  'Dayloom turns your thoughts into a manageable day. You stay in charge of every action.',
                )}
              </p>
              <div className="guide-concepts">
                <div>
                  <MessageSquare size={22} />
                  <h3>{t('Tell your assistant')}</h3>
                  <p>
                    {t(
                      'Describe a task or a plan in your own words. Your connected model can suggest tasks, memories and briefs.',
                    )}
                  </p>
                </div>
                <div>
                  <ShieldCheck size={22} />
                  <h3>{t('Review before anything happens')}</h3>
                  <p>
                    {t(
                      'A suggestion is not an executed action. You can edit, approve or cancel each proposal in Activity.',
                    )}
                  </p>
                </div>
                <div>
                  <CircleCheck size={22} />
                  <h3>{t('Make room for your day')}</h3>
                  <p>
                    {t(
                      'Today organizes tasks around your available time. Memories and calendar imports can be added later in Settings.',
                    )}
                  </p>
                </div>
              </div>
              <img
                className="guide-image"
                src="/workspace.png"
                alt={t('Illustration of a notebook and a plant on a sunlit desk')}
              />
              <p className="guide-note">
                {t(
                  'Have these ready: an API base URL, a model ID and an API key from your provider. No payment or purchase is made by this guide.',
                )}
              </p>
              <div className="guide-actions">
                <button className="button" onClick={() => moveTo(1)}>
                  {t('Set up my model')}
                  <ArrowRight size={16} />
                </button>
              </div>
            </div>
          )}
          {activeStep === 1 && (
            <>
              <p className="guide-lead">
                {t(
                  'Paste the three values from your model provider. The key stays out of conversations and tutorial progress.',
                )}
              </p>
              {configuration.isPending ? (
                <p role="status">{t('Loading model connection...')}</p>
              ) : configuration.data ? (
                <>
                  {connection?.managed === 'workspace' && connection.configured && (
                    <div className="guide-existing">
                      <KeyRound size={20} />
                      <div>
                        <strong>{connection.model}</strong>
                        <p>
                          {t(
                            'A connection is already saved. You can test it or replace its credentials below.',
                          )}
                        </p>
                      </div>
                      <button
                        className="button secondary"
                        disabled={busy}
                        onClick={() => {
                          setVerifiedFor('')
                          moveTo(2)
                        }}
                      >
                        {t('Use saved connection')}
                        <ArrowRight size={15} />
                      </button>
                    </div>
                  )}
                  <ModelConnectionForm
                    key={`${connection?.version ?? 0}:${connection?.managed}`}
                    configuration={configuration.data}
                    guided
                    onSaved={() => {
                      setVerifiedFor('')
                      setTestConsent(false)
                      moveTo(2)
                    }}
                  />
                </>
              ) : (
                <div role="alert">
                  <p>{t('Model settings unavailable.')}</p>
                  <button className="button secondary" onClick={() => void configuration.refetch()}>
                    {t('Retry')}
                  </button>
                </div>
              )}
            </>
          )}
          {activeStep === 2 && (
            <>
              <p className="guide-lead">
                {t(
                  'Saving is not the same as connecting. This check asks your provider for a short response without sending your workspace content or executing proposals.',
                )}
              </p>
              {progress.step >= 3 && !verified && (
                <p className="guide-note">
                  {t(
                    'Please test this connection again after returning to the guide or changing its configuration.',
                  )}
                </p>
              )}
              {connection?.managed === 'workspace' && connection.configured ? (
                <>
                  <dl className="guide-connection">
                    <div>
                      <dt>{t('API base URL')}</dt>
                      <dd>{connection.base_url}</dd>
                    </div>
                    <div>
                      <dt>{t('Model')}</dt>
                      <dd>{connection.model}</dd>
                    </div>
                  </dl>
                  <label className="consent">
                    <input
                      type="checkbox"
                      checked={testConsent}
                      onChange={(event) => setTestConsent(event.target.checked)}
                    />
                    <span>
                      {t(
                        'I agree to one real API test. It counts toward my daily limit and my provider may charge for it.',
                      )}
                    </span>
                  </label>
                  {verified && (
                    <p className="guide-success" role="status">
                      <CircleCheck size={20} />
                      {t('Connection verified. Your model is ready.')}
                    </p>
                  )}
                  <div className="guide-actions">
                    <button
                      className="button"
                      disabled={busy || !testConsent}
                      onClick={() =>
                        void perform(async () => {
                          const result = await api<{ connected: boolean }>(
                            '/api/models/test',
                            'POST',
                          )
                          if (!result.connected)
                            throw new Error('The provider did not confirm the connection.')
                          await client.invalidateQueries({ queryKey: ['model-configuration'] })
                          setVerifiedFor(fingerprint)
                        })
                      }
                    >
                      {busy ? <LoaderCircle size={16} className="spin" /> : <Plug size={16} />}
                      {t(busy ? 'Testing connection...' : 'Test connection')}
                    </button>
                    {verified && (
                      <button
                        className="button secondary"
                        disabled={busy}
                        onClick={() => moveTo(3)}
                      >
                        {t('Try my first message')}
                        <ArrowRight size={16} />
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <button className="button" disabled={busy} onClick={() => moveTo(1)}>
                  <KeyRound size={16} />
                  {t('Connect model')}
                </button>
              )}
              <details className="guide-help">
                <summary>{t('Connection did not work?')}</summary>
                <ul>
                  <li>{t('Check that the API key is active and has credit or quota.')}</li>
                  <li>
                    {t('Use a model ID your API account can access, not a display nickname.')}
                  </li>
                  <li>
                    {t(
                      'Check the base URL and approved domain. The service must support Chat Completions and JSON object responses.',
                    )}
                  </li>
                </ul>
              </details>
            </>
          )}
          {activeStep === 3 && (
            <>
              <p className="guide-lead">
                {t(
                  'Start with a small task. You can edit this example before sending it. Nothing is approved automatically.',
                )}
              </p>
              <form
                onSubmit={async (event) => {
                  event.preventDefault()
                  if (!chatConsent || !verified || !message.trim()) return
                  await perform(async () => {
                    const result = await api<{ message: Message; actions: Action[] }>(
                      '/api/chat',
                      'POST',
                      { content: message.trim(), allow_external: true },
                    )
                    setReply(result)
                    moveTo(4)
                  })
                }}
              >
                <label>
                  {t('Your first message')}
                  <textarea
                    value={message}
                    onChange={(event) => setDraftMessage(event.target.value)}
                    required
                    maxLength={10000}
                  />
                </label>
                <label className="consent">
                  <input
                    type="checkbox"
                    checked={chatConsent}
                    onChange={(event) => setChatConsent(event.target.checked)}
                  />
                  <span>
                    {t(
                      'Share this message, recent conversation, task titles, active memories and connected sender addresses with {{model}}. API usage may be charged by my provider.',
                      { model: connection?.model },
                    )}
                  </span>
                </label>
                <div className="guide-actions">
                  <button
                    className="button"
                    type="submit"
                    disabled={busy || !chatConsent || !message.trim() || !verified}
                  >
                    {busy ? (
                      <LoaderCircle size={16} className="spin" />
                    ) : (
                      <MessageSquare size={16} />
                    )}
                    {t(busy ? 'Working...' : 'Send my first message')}
                  </button>
                </div>
              </form>
            </>
          )}
          {activeStep === 4 && reply && (
            <>
              <p className="guide-success">
                <CircleCheck size={20} />
                {t('Your first conversation is ready.')}
              </p>
              <div className="guide-reply">
                <strong>Dayloom</strong>
                <p>{reply.message.content}</p>
              </div>
              <p className="guide-lead">
                {t(
                  'Check the exact details below. Approve only what you want done; cancel or revise anything else. The worker must be online to execute approved actions.',
                )}
              </p>
              {!data.settings.worker_online && (
                <p className="inline-error" role="status">
                  {t(
                    'The worker is offline. Approved actions will wait until your server worker is running.',
                  )}
                </p>
              )}
              <div className="guide-proposals">
                {reply.actions.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={data.actions.find((current) => current.id === action.id) ?? action}
                  />
                ))}
              </div>
              {!reply.actions.length && (
                <p className="guide-note">
                  {t(
                    'The model replied without proposing an action. You can keep talking in Inbox or create a task yourself.',
                  )}
                </p>
              )}
              <div className="guide-actions">
                <button
                  className="button"
                  disabled={busy}
                  onClick={() => {
                    moveTo(4, true)
                    navigate('/today')
                  }}
                >
                  {t('Enter my workspace')}
                  <ArrowRight size={16} />
                </button>
                <Link className="button secondary" to="/inbox">
                  {t('Continue conversation')}
                </Link>
              </div>
              <p className="guide-note">
                {t(
                  'You can reopen this guide from the sidebar or Settings. Calendar, memory, email and device access are optional next steps.',
                )}
              </p>
            </>
          )}
          {failure && (
            <div className="guide-error" role="alert">
              <strong>
                {t('This step did not finish. You can retry or edit the connection.')}
              </strong>
              <p>{t(failure)}</p>
            </div>
          )}
          <div className="guide-footer">
            {activeStep > 0 && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() => moveTo(activeStep - 1)}
              >
                <ArrowLeft size={15} />
                {t('Back')}
              </button>
            )}
            <button
              className="text-button"
              disabled={busy}
              onClick={() => {
                moveTo(activeStep)
                navigate('/today')
              }}
            >
              {t('Continue later')}
            </button>
            <button
              className="text-button"
              disabled={busy}
              onClick={() => {
                setVerifiedFor('')
                setReply(null)
                setChatConsent(false)
                setTestConsent(false)
                setDraftMessage(null)
                moveTo(0)
              }}
            >
              <RotateCcw size={14} />
              {t('Start over')}
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

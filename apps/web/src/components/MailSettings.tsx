import { useTranslation } from 'react-i18next'
import { useId, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Mail, Pencil, Plug, Plus, Save, Trash2 } from 'lucide-react'
import { api } from '../api'
import { useWorkspace } from '../useWorkspace'
import { ConfirmDelete, IconButton, Modal } from './ui'

interface MailConnection {
  id: string
  label: string
  kind: string
  version: number
  configuration: { host: string; username: string }
}
interface Connections {
  connections: MailConnection[]
  smtp_hosts: string[]
  mail_daily_limit: number
}

function MailEditor({ connection, onClose }: { connection: MailConnection; onClose: () => void }) {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const [recipients, setRecipients] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  return (
    <Modal title={t('Prepare email')} onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          if (
            await execute(
              () =>
                api('/api/actions', 'POST', {
                  tool: 'SendEmail',
                  payload: {
                    connection_id: connection.id,
                    connection_version: connection.version,
                    sender: connection.configuration.username,
                    to: recipients.split(',').map((address) => address.trim()),
                    subject,
                    body,
                  },
                }),
              'Email ready for approval.',
            )
          )
            onClose()
        }}
      >
        <label>
          {t('From')}
          <input type="email" readOnly value={connection.configuration.username} />
        </label>
        <label>
          {t('To')}
          <input
            type="email"
            multiple
            required
            value={recipients}
            onChange={(event) => setRecipients(event.target.value)}
          />
        </label>
        <label>
          {t('Subject')}
          <input
            required
            maxLength={300}
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
          />
        </label>
        <label>
          {t('Message')}
          <textarea
            required
            maxLength={20000}
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
        </label>
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button type="submit" className="button" disabled={busy}>
            <Mail size={15} />
            {t('Create proposal')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function MailSettings() {
  const { t } = useTranslation()

  const passwordHelpId = useId()
  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api<Connections>('/api/integrations'),
  })
  const [connecting, setConnecting] = useState(false)
  const [editing, setEditing] = useState<MailConnection | null>(null)
  const [verifying, setVerifying] = useState<MailConnection | null>(null)
  const [testConsent, setTestConsent] = useState(false)
  const [verificationResults, setVerificationResults] = useState<
    Record<string, { success: boolean; message: string }>
  >({})
  const [composing, setComposing] = useState<MailConnection | null>(null)
  const [removing, setRemoving] = useState<MailConnection | null>(null)
  const [draft, setDraft] = useState({ label: '', host: '', username: '', password: '' })
  const passwordRequired =
    !editing ||
    draft.host !== editing.configuration.host ||
    draft.username !== editing.configuration.username
  const verification = verifying
    ? verificationResults[`${verifying.id}:${verifying.version}`]
    : undefined
  function closeEditor() {
    setConnecting(false)
    setEditing(null)
    setDraft((current) => ({ ...current, password: '' }))
  }
  return (
    <section className="settings-section">
      <div className="settings-section-title">
        <Mail size={19} />
        <div>
          <h2>{t('Email accounts')}</h2>
          <span>{t('Encrypted SMTP credentials')}</span>
        </div>
      </div>
      <div className="settings-body">
        {query.error && <p role="alert">{query.error.message}</p>}
        {query.data?.connections
          .filter((connection) => connection.kind === 'smtp')
          .map((connection) => (
            <div className="connection-row mail-connection-row" key={connection.id}>
              <span className="connection-icon">
                <Mail size={20} />
              </span>
              <div>
                <strong>{connection.label}</strong>
                <span>{connection.configuration.username}</span>
                <span>
                  {t(
                    verificationResults[`${connection.id}:${connection.version}`]?.success
                      ? 'Sign-in verified'
                      : verificationResults[`${connection.id}:${connection.version}`]
                        ? 'Verification failed'
                        : 'Saved, not verified',
                  )}
                </span>
              </div>
              <button
                className="button secondary compact"
                disabled={busy}
                onClick={() => {
                  setVerifying(connection)
                  setTestConsent(false)
                }}
              >
                <Plug size={15} />
                {t('Verify account')}
              </button>
              <button className="button secondary" onClick={() => setComposing(connection)}>
                <Mail size={15} />
                {t('Prepare email')}
              </button>
              <IconButton
                icon={Pencil}
                label={t('Edit {{title}}', { title: connection.label })}
                disabled={busy}
                onClick={() => {
                  setEditing(connection)
                  setDraft({ label: connection.label, ...connection.configuration, password: '' })
                  setConnecting(true)
                }}
              />
              <button
                className="icon-button"
                title={t('Disconnect email')}
                aria-label={t('Disconnect {{name}}', { name: connection.label })}
                onClick={() => setRemoving(connection)}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        <button
          className="button secondary"
          disabled={!query.data}
          onClick={() => {
            setEditing(null)
            setDraft({
              label: '',
              host: query.data!.smtp_hosts[0] ?? '',
              username: '',
              password: '',
            })
            setConnecting(true)
          }}
        >
          <Plus size={15} />
          {t('Connect email')}
        </button>
      </div>
      {connecting && (
        <Modal
          title={t(editing ? 'Edit email account' : 'Connect email account')}
          onClose={closeEditor}
        >
          <form
            onSubmit={async (event) => {
              event.preventDefault()
              if (
                await execute(async () => {
                  await api(
                    editing ? `/api/integrations/smtp/${editing.id}` : '/api/integrations/smtp',
                    editing ? 'PUT' : 'POST',
                    editing
                      ? { ...draft, password: draft.password || null, version: editing.version }
                      : draft,
                  )
                  await client.invalidateQueries({ queryKey: ['integrations'] })
                }, 'Email settings saved. Verify the account before sending.')
              ) {
                closeEditor()
              }
            }}
          >
            <label>
              {t('Account label')}
              <input
                required
                maxLength={100}
                value={draft.label}
                onChange={(event) => setDraft({ ...draft, label: event.target.value })}
              />
            </label>
            <label>
              {t('SMTP server')}
              <select
                required
                value={draft.host}
                onChange={(event) => setDraft({ ...draft, host: event.target.value, password: '' })}
              >
                {query.data?.smtp_hosts.map((host) => (
                  <option key={host}>{host}</option>
                ))}
              </select>
            </label>
            <label>
              {t('Email address')}
              <input
                type="email"
                autoComplete="username"
                required
                value={draft.username}
                onChange={(event) =>
                  setDraft({ ...draft, username: event.target.value, password: '' })
                }
              />
            </label>
            <label>
              {t('App password')}
              <input
                type="password"
                autoComplete="new-password"
                required={passwordRequired}
                maxLength={4096}
                aria-describedby={passwordHelpId}
                placeholder={
                  editing && !passwordRequired
                    ? t('Leave blank to keep the saved password')
                    : undefined
                }
                value={draft.password}
                onChange={(event) => setDraft({ ...draft, password: event.target.value })}
              />
            </label>
            <div className="field-help" id={passwordHelpId}>
              <p>
                {t(
                  'This is a code generated by your email provider for apps, not your normal sign-in password. Look for App passwords or SMTP authorization in your email account security settings.',
                )}
              </p>
              <p>
                {t(
                  'Your provider may require two-step verification or enabling SMTP first. Work accounts may need administrator approval.',
                )}
              </p>
              <p>
                {t(
                  'Saving only stores your settings. Verify the account to check sign-in; no email is sent during verification.',
                )}
              </p>
              {editing && (
                <p>
                  {t(
                    'Changing the email address or server requires a new app password. Existing unsent proposals must be recreated with the updated connection.',
                  )}
                </p>
              )}
            </div>
            <div className="form-actions">
              <button type="button" className="button secondary" onClick={closeEditor}>
                {t('Cancel')}
              </button>
              <button type="submit" className="button" disabled={busy}>
                <Save size={15} />
                {t('Save connection')}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {verifying && (
        <Modal title={t('Verify email account')} onClose={() => setVerifying(null)}>
          <p>{verifying.configuration.username}</p>
          <label className="consent">
            <input
              type="checkbox"
              checked={testConsent}
              onChange={(event) => setTestConsent(event.target.checked)}
            />
            <span>
              {t('Allow a sign-in check with {{server}}. No email will be sent.', {
                server: verifying.configuration.host,
              })}
            </span>
          </label>
          {verification && (
            <p
              className={verification.success ? 'field-help' : 'inline-error'}
              role={verification.success ? 'status' : 'alert'}
            >
              {t(verification.message)}
            </p>
          )}
          <div className="form-actions">
            <button className="button secondary" onClick={() => setVerifying(null)}>
              {t('Close dialog')}
            </button>
            <button
              className="button"
              disabled={busy || !testConsent}
              onClick={() => {
                const key = `${verifying.id}:${verifying.version}`
                void execute(async () => {
                  try {
                    await api(`/api/integrations/smtp/${verifying.id}/test`, 'POST', {
                      version: verifying.version,
                      allow_external: testConsent,
                    })
                    setVerificationResults((current) => ({
                      ...current,
                      [key]: {
                        success: true,
                        message:
                          'Email sign-in verified. No email was sent; delivery is not guaranteed by this check.',
                      },
                    }))
                  } catch (error) {
                    setVerificationResults((current) => ({
                      ...current,
                      [key]: {
                        success: false,
                        message:
                          error instanceof Error
                            ? error.message
                            : 'Could not reach the email server. Check the connection and try again.',
                      },
                    }))
                    throw error
                  }
                })
              }}
            >
              <Plug size={15} />
              {t('Verify account')}
            </button>
          </div>
        </Modal>
      )}
      {composing && <MailEditor connection={composing} onClose={() => setComposing(null)} />}
      {removing && (
        <ConfirmDelete
          title={t('Disconnect this email account?')}
          busy={busy}
          onClose={() => setRemoving(null)}
          onConfirm={() =>
            void execute(async () => {
              await api(`/api/integrations/${removing.id}`, 'DELETE')
              await client.invalidateQueries({ queryKey: ['integrations'] })
            }, 'Email disconnected.').then((success) => {
              if (success) setRemoving(null)
            })
          }
        />
      )}
    </section>
  )
}

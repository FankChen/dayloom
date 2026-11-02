import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Mail, Plus, Save, Trash2 } from 'lucide-react'
import { api } from '../api'
import { useWorkspace } from '../useWorkspace'
import { ConfirmDelete, Modal } from './ui'

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
  const { busy, execute } = useWorkspace()
  const [recipients, setRecipients] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  return (
    <Modal title="Prepare email" onClose={onClose}>
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
          From
          <input type="email" readOnly value={connection.configuration.username} />
        </label>
        <label>
          To
          <input
            type="email"
            multiple
            required
            value={recipients}
            onChange={(event) => setRecipients(event.target.value)}
          />
        </label>
        <label>
          Subject
          <input
            required
            maxLength={300}
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
          />
        </label>
        <label>
          Message
          <textarea
            required
            maxLength={20000}
            value={body}
            onChange={(event) => setBody(event.target.value)}
          />
        </label>
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="button" disabled={busy}>
            <Mail size={15} />
            Create proposal
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function MailSettings() {
  const { busy, execute } = useWorkspace()
  const client = useQueryClient()
  const query = useQuery({
    queryKey: ['integrations'],
    queryFn: () => api<Connections>('/api/integrations'),
  })
  const [connecting, setConnecting] = useState(false)
  const [composing, setComposing] = useState<MailConnection | null>(null)
  const [removing, setRemoving] = useState<MailConnection | null>(null)
  const [draft, setDraft] = useState({ label: '', host: '', username: '', password: '' })
  return (
    <section className="settings-section">
      <div className="settings-section-title">
        <Mail size={19} />
        <div>
          <h2>Email accounts</h2>
          <span>Encrypted SMTP credentials</span>
        </div>
      </div>
      <div className="settings-body">
        {query.error && <p role="alert">{query.error.message}</p>}
        {query.data?.connections
          .filter((connection) => connection.kind === 'smtp')
          .map((connection) => (
            <div className="connection-row" key={connection.id}>
              <span className="connection-icon">
                <Mail size={20} />
              </span>
              <div>
                <strong>{connection.label}</strong>
                <span>{connection.configuration.username}</span>
              </div>
              <button className="button secondary" onClick={() => setComposing(connection)}>
                <Mail size={15} />
                Prepare email
              </button>
              <button
                className="icon-button"
                title="Disconnect email"
                aria-label={`Disconnect ${connection.label}`}
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
          Connect email
        </button>
      </div>
      {connecting && (
        <Modal title="Connect email account" onClose={() => setConnecting(false)}>
          <form
            onSubmit={async (event) => {
              event.preventDefault()
              if (
                await execute(async () => {
                  await api('/api/integrations/smtp', 'POST', draft)
                  await client.invalidateQueries({ queryKey: ['integrations'] })
                }, 'Email connection saved.')
              ) {
                setDraft({ ...draft, password: '' })
                setConnecting(false)
              }
            }}
          >
            <label>
              Account label
              <input
                required
                maxLength={100}
                value={draft.label}
                onChange={(event) => setDraft({ ...draft, label: event.target.value })}
              />
            </label>
            <label>
              SMTP server
              <select
                required
                value={draft.host}
                onChange={(event) => setDraft({ ...draft, host: event.target.value })}
              >
                {query.data?.smtp_hosts.map((host) => (
                  <option key={host}>{host}</option>
                ))}
              </select>
            </label>
            <label>
              Email address
              <input
                type="email"
                autoComplete="username"
                required
                value={draft.username}
                onChange={(event) => setDraft({ ...draft, username: event.target.value })}
              />
            </label>
            <label>
              App password
              <input
                type="password"
                autoComplete="new-password"
                required
                value={draft.password}
                onChange={(event) => setDraft({ ...draft, password: event.target.value })}
              />
            </label>
            <div className="form-actions">
              <button
                type="button"
                className="button secondary"
                onClick={() => setConnecting(false)}
              >
                Cancel
              </button>
              <button type="submit" className="button" disabled={busy}>
                <Save size={15} />
                Save connection
              </button>
            </div>
          </form>
        </Modal>
      )}
      {composing && <MailEditor connection={composing} onClose={() => setComposing(null)} />}
      {removing && (
        <ConfirmDelete
          title="Disconnect this email account?"
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

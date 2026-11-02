import { useState } from 'react'
import {
  Check,
  CircleCheck,
  Clock3,
  FileText,
  Leaf,
  Pencil,
  RotateCcw,
  ShieldCheck,
  X,
  type LucideIcon,
} from 'lucide-react'
import { api, formatTime } from '../api'
import type { Action } from '../types'
import { useWorkspace } from '../useWorkspace'
import { IconButton, Modal, Status } from './ui'
import { OutcomeDialog, ScheduleDialog } from './AutomationControls'

const toolIcons: Record<string, LucideIcon> = {
  CreateTask: CircleCheck,
  SaveMemory: Leaf,
  PrepareBrief: FileText,
}
const toolLabels: Record<string, string> = {
  CreateTask: 'Create a task',
  SaveMemory: 'Remember a detail',
  PrepareBrief: 'Prepare a daily brief',
}

function ActionEditor({ action, onClose }: { action: Action; onClose: () => void }) {
  const { busy, execute } = useWorkspace()
  const [payload, setPayload] = useState(action.payload)
  const [digest] = useState(action.digest)
  const [externalText, setExternalText] = useState(JSON.stringify(action.payload, null, 2))
  const [jsonError, setJsonError] = useState('')
  function field(key: string, value: unknown) {
    setPayload({ ...payload, [key]: value })
  }
  return (
    <Modal title="Revise action" onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          let revised = payload
          if (!(action.tool in toolIcons)) {
            try {
              revised = JSON.parse(externalText) as Record<string, unknown>
            } catch {
              setJsonError('Enter a valid JSON action payload.')
              return
            }
          }
          if (
            await execute(
              () => api(`/api/actions/${action.id}`, 'PATCH', { digest, payload: revised }),
              'Action revised. A new approval is required.',
            )
          )
            onClose()
        }}
      >
        {action.tool === 'CreateTask' && (
          <>
            <label>
              Task title
              <input
                required
                maxLength={200}
                value={String(payload.title ?? '')}
                onChange={(event) => field('title', event.target.value)}
              />
            </label>
            <label>
              Notes
              <textarea
                maxLength={5000}
                value={String(payload.notes ?? '')}
                onChange={(event) => field('notes', event.target.value)}
              />
            </label>
            <div className="form-grid">
              <label>
                Estimate (minutes)
                <input
                  type="number"
                  required
                  min={5}
                  max={480}
                  step={5}
                  value={Number(payload.minutes ?? 30)}
                  onChange={(event) => field('minutes', Number(event.target.value))}
                />
              </label>
              <label>
                Priority
                <select
                  value={String(payload.priority ?? 'normal')}
                  onChange={(event) => field('priority', event.target.value)}
                >
                  <option value="high">High</option>
                  <option value="normal">Normal</option>
                  <option value="low">Low</option>
                </select>
              </label>
            </div>
            <label>
              Due date
              <input
                type="date"
                value={String(payload.due_date ?? '')}
                onChange={(event) => field('due_date', event.target.value || null)}
              />
            </label>
          </>
        )}
        {action.tool === 'SaveMemory' && (
          <>
            <label>
              Memory
              <textarea
                required
                maxLength={3000}
                value={String(payload.content ?? '')}
                onChange={(event) => field('content', event.target.value)}
              />
            </label>
            <label>
              Category
              <select
                value={String(payload.category ?? 'preference')}
                onChange={(event) => field('category', event.target.value)}
              >
                <option value="preference">Preference</option>
                <option value="goal">Goal</option>
                <option value="fact">Fact</option>
                <option value="context">Temporary context</option>
              </select>
            </label>
            <label>
              Expires on
              <input
                type="date"
                value={String(payload.expires_on ?? '')}
                onChange={(event) => field('expires_on', event.target.value || null)}
              />
            </label>
          </>
        )}
        {action.tool === 'PrepareBrief' && (
          <label>
            Day
            <input
              type="date"
              required
              value={String(payload.day ?? '')}
              onChange={(event) => field('day', event.target.value)}
            />
          </label>
        )}
        {!(action.tool in toolIcons) && (
          <label>
            Exact action payload
            <textarea
              className="payload-editor"
              required
              value={externalText}
              onChange={(event) => {
                setExternalText(event.target.value)
                setJsonError('')
              }}
            />
          </label>
        )}
        {jsonError && (
          <p className="inline-error" role="alert">
            {jsonError}
          </p>
        )}
        <div className="form-actions">
          <button className="button secondary" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="button" type="submit" disabled={busy}>
            Save revision
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function ActionCard({ action }: { action: Action }) {
  const { data, busy, execute } = useWorkspace()
  const [editing, setEditing] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [resolving, setResolving] = useState(false)
  const definition = data?.settings.tools.find((tool) => tool.name === action.tool)
  const Icon = toolIcons[action.tool] ?? ShieldCheck
  const title = String(
    action.payload.title ??
      action.payload.subject ??
      action.payload.content ??
      action.payload.day ??
      action.payload.url ??
      '',
  )
  return (
    <article className={`action-item action-${action.status}`}>
      <div className="action-heading">
        <span className="action-icon">
          <Icon size={17} />
        </span>
        <strong>{toolLabels[action.tool] ?? definition?.label ?? action.tool}</strong>
        <Status value={action.status} />
      </div>
      <p className="action-title">{title}</p>
      {!(action.tool in toolIcons) && (
        <dl className="payload-fields">
          {Object.entries(action.payload).map(([name, value]) => (
            <div key={name}>
              <dt>{name.replaceAll('_', ' ')}</dt>
              <dd>{typeof value === 'string' ? value : JSON.stringify(value)}</dd>
            </div>
          ))}
        </dl>
      )}
      {action.tool === 'CreateTask' && (
        <div className="action-metadata">
          <span>{String(action.payload.minutes ?? 30)} min</span>
          <span>{String(action.payload.priority ?? 'normal')} priority</span>
          {Boolean(action.payload.due_date) && <span>Due {String(action.payload.due_date)}</span>}
        </div>
      )}
      {action.error && <p className="inline-error">{action.error}</p>}
      {action.result && (
        <div className="action-result">
          <span>
            <Check size={14} />
            {action.result.title}
          </span>
          {action.result.text && <pre className="payload-preview">{action.result.text}</pre>}
          {action.result.plan && (
            <ul>
              {action.result.plan.items.map((item) => (
                <li key={item.task_id}>
                  <span>{formatTime(item.start, action.result?.plan?.timezone)}</span>
                  {item.title}
                </li>
              ))}
              {action.result.plan.items.length === 0 && (
                <li>No available focus blocks for this day.</li>
              )}
            </ul>
          )}
        </div>
      )}
      <div className="action-footer">
        <span className="approval-note">
          <ShieldCheck size={13} />
          {action.status === 'pending' ? 'Awaiting your approval' : `Attempt ${action.attempts}`}
        </span>
        <div className="row-actions">
          {action.status === 'outcome_unknown' && (
            <button className="button secondary small-button" onClick={() => setResolving(true)}>
              <ShieldCheck size={14} />
              Record checked outcome
            </button>
          )}
          {action.status === 'pending' && definition?.automation_allowed && (
            <button className="button secondary small-button" onClick={() => setScheduling(true)}>
              <Clock3 size={14} />
              Schedule
            </button>
          )}
          {['pending', 'queued', 'failed'].includes(action.status) && (
            <IconButton icon={Pencil} label="Revise action" onClick={() => setEditing(true)} />
          )}
          {['pending', 'queued', 'failed'].includes(action.status) && (
            <IconButton
              icon={X}
              label="Cancel action"
              disabled={busy}
              onClick={() =>
                void execute(
                  () => api(`/api/actions/${action.id}/cancel`, 'POST'),
                  'Action cancelled.',
                )
              }
            />
          )}
          {action.status === 'failed' && (
            <button
              className="button secondary small-button"
              disabled={busy}
              onClick={() =>
                void execute(
                  () => api(`/api/actions/${action.id}/retry`, 'POST'),
                  'Ready for review. Approval is required again.',
                )
              }
            >
              <RotateCcw size={14} />
              Retry
            </button>
          )}
          {action.status === 'pending' && (
            <button
              className="button small-button"
              disabled={busy}
              onClick={() =>
                void execute(
                  () => api(`/api/actions/${action.id}/approve`, 'POST', { digest: action.digest }),
                  'Approved. The worker will pick this up.',
                )
              }
            >
              <Check size={14} />
              Approve
            </button>
          )}
        </div>
      </div>
      <details className="execution-details">
        <summary>Execution details</summary>
        <dl>
          <dt>Action ID</dt>
          <dd>{action.id}</dd>
          <dt>Content hash</dt>
          <dd>{action.digest}</dd>
          <dt>Created</dt>
          <dd>{new Date(action.created_at).toLocaleString()}</dd>
        </dl>
      </details>
      {editing && <ActionEditor action={action} onClose={() => setEditing(false)} />}
      {scheduling && <ScheduleDialog action={action} onClose={() => setScheduling(false)} />}
      {resolving && <OutcomeDialog action={action} onClose={() => setResolving(false)} />}
    </article>
  )
}

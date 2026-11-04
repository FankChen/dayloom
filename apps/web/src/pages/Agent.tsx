import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  Check,
  Download,
  FileText,
  Globe,
  Mail,
  MessageSquare,
  Pause,
  Play,
  Plug,
  Search,
  ShieldCheck,
  ShoppingBag,
  Ticket,
  X,
} from 'lucide-react'
import { api, formatDateTime } from '../api'
import { ActionCard } from '../components/ActionCard'
import { DeviceConnections } from '../components/DeviceConnections'
import { EmptyState, IconButton, Modal, PageHeader } from '../components/ui'
import type { AgentCatalog, AgentRun, WorkArtifact } from '../types'
import { useWorkspace } from '../useWorkspace'

const runLabels: Record<string, string> = {
  queued: 'Agent queued',
  planning: 'Planning next step',
  waiting_approval: 'Waiting for tool approval',
  needs_input: 'Needs your input',
  paused: 'Agent paused',
  completed: 'Agent completed',
  cancelled: 'Agent cancelled',
}
const templates = [
  {
    label: 'Research and save',
    icon: Search,
    tools: ['SearchWeb', 'ReadWebPage', 'SaveArtifact'],
    goal: 'Research a topic, compare reliable sources and save a source-linked note. Ask me for the topic first.',
  },
  {
    label: 'Prepare an email',
    icon: Mail,
    tools: ['SearchWeb', 'SaveArtifact', 'SendEmail'],
    goal: 'Help me prepare an email. Ask for the recipient and purpose, draft it for my review, and send only after I approve the exact content.',
  },
  {
    label: 'Plan a movie booking',
    icon: Ticket,
    tools: ['SearchWeb', 'ListDeviceTools', 'CallDeviceTool'],
    goal: 'Help me find movie showtimes. Ask for my city, film, date and budget. Use only an authorized device tool if available. Do not buy or pay without my explicit confirmation.',
  },
  {
    label: 'Plan a food order',
    icon: ShoppingBag,
    tools: ['SearchWeb', 'ListDeviceTools', 'CallDeviceTool'],
    goal: 'Help me choose a food order. Ask for my location, preferences and budget. Explain which ordering tools are available. Do not place an order or pay without my explicit confirmation.',
  },
  {
    label: 'Find software',
    icon: Download,
    tools: ['SearchWeb', 'ListDeviceTools', 'CallDeviceTool'],
    goal: 'Find official software sources. Ask for the software name and my operating system. Download only an approved catalog package on my connected device; never install it automatically.',
  },
]

function ContinueRun({
  run,
  external,
  onClose,
}: {
  run: AgentRun
  external: boolean
  onClose: () => void
}) {
  const { t } = useTranslation()
  const { busy, execute } = useWorkspace()
  const [message, setMessage] = useState('')
  const [maxSteps, setMaxSteps] = useState(Math.min(24, Math.max(run.max_steps, run.steps + 4)))
  const [consent, setConsent] = useState(false)
  return (
    <Modal title={t('Continue Agent run')} onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          if (
            await execute(
              () =>
                api(`/api/agent/runs/${run.id}/resume`, 'POST', {
                  message,
                  max_steps: maxSteps,
                  allow_external: consent,
                }),
              'Agent run continued.',
            )
          )
            onClose()
        }}
      >
        <label>
          {t('Your clarification')}
          <textarea
            required={run.status === 'needs_input'}
            maxLength={10000}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </label>
        <label>
          {t('Total step limit')}
          <input
            type="number"
            required
            min={Math.min(24, run.steps + 1)}
            max={24}
            value={maxSteps}
            onChange={(event) => setMaxSteps(Number(event.target.value))}
          />
        </label>
        <p className="field-help">
          {t(
            'Continuing renews this goal for one hour and cancels old pending proposals. Device actions still need separate approval.',
          )}
        </p>
        {external && (
          <label className="consent">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            <span>
              {t(
                'Allow this goal, clarifications, connection metadata and tool results to be shared with the configured model. Agent calls may incur provider charges.',
              )}
            </span>
          </label>
        )}
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button
            className="button"
            disabled={busy || maxSteps <= run.steps || (external && !consent)}
          >
            <Play size={16} />
            {t('Continue Agent run')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function ArtifactViewer({ artifact, onClose }: { artifact: WorkArtifact; onClose: () => void }) {
  const { t } = useTranslation()
  const downloadLink = useRef<HTMLAnchorElement>(null)
  useEffect(() => {
    const url = URL.createObjectURL(
      new Blob([artifact.content ?? ''], { type: 'text/markdown;charset=utf-8' }),
    )
    const link = downloadLink.current
    if (link) link.href = url
    return () => {
      link?.removeAttribute('href')
      URL.revokeObjectURL(url)
    }
  }, [artifact.id, artifact.content])
  return (
    <Modal title={artifact.title} onClose={onClose}>
      <pre className="agent-artifact-content">{artifact.content}</pre>
      <ul className="agent-source-links">
        {artifact.sources.map((source) => (
          <li key={source}>
            <a href={source} target="_blank" rel="noopener noreferrer">
              <Globe size={13} />
              {source}
            </a>
          </li>
        ))}
      </ul>
      <div className="form-actions">
        <a
          className="button"
          ref={downloadLink}
          download={`${artifact.id}.md`}
        >
          <Download size={16} />
          {t('Download Markdown')}
        </a>
      </div>
    </Modal>
  )
}

export function Agent() {
  const { t } = useTranslation()
  const { data, busy, execute } = useWorkspace()
  const [params, setParams] = useSearchParams()
  const [goal, setGoal] = useState('')
  const [selectedTools, setSelectedTools] = useState(['SearchWeb', 'SaveArtifact'])
  const [maxSteps, setMaxSteps] = useState(8)
  const [consent, setConsent] = useState(false)
  const [autoReadonly, setAutoReadonly] = useState(false)
  const [continuing, setContinuing] = useState(false)
  const [artifact, setArtifact] = useState<WorkArtifact | null>(null)
  const workspaceId = data?.account.workspace_id
  const catalog = useQuery({
    queryKey: ['agent', workspaceId, 'catalog'],
    queryFn: () => api<AgentCatalog>('/api/agent/tools'),
    refetchInterval: 10000,
  })
  const runs = useQuery({
    queryKey: ['agent', workspaceId, 'runs'],
    queryFn: () => api<AgentRun[]>('/api/agent/runs'),
    refetchInterval: 2000,
  })
  const selectedId = params.get('run') ?? runs.data?.[0]?.id ?? ''
  const detail = useQuery({
    queryKey: ['agent', workspaceId, 'run', selectedId],
    queryFn: () => api<AgentRun>(`/api/agent/runs/${selectedId}`),
    enabled: !!selectedId,
    refetchInterval: 2000,
  })
  const artifacts = useQuery({
    queryKey: ['agent', workspaceId, 'artifacts'],
    queryFn: () => api<WorkArtifact[]>('/api/artifacts'),
    refetchInterval: 5000,
  })
  const tab = params.get('view') ?? 'runs'
  const available = catalog.data?.tools.filter((tool) => tool.available) ?? []
  const allowedTools = selectedTools.filter((name) => available.some((tool) => tool.name === name))
  const run = detail.data
  const latestAction = run?.steps_history?.at(-1)?.action
  const statusLabel =
    run?.status === 'waiting_approval' && latestAction?.status === 'running'
      ? 'Agent tool running'
      : run?.status === 'waiting_approval' && latestAction?.status === 'queued'
        ? 'Agent tool queued'
        : runLabels[run?.status ?? 'queued']
  const error = catalog.error ?? runs.error ?? detail.error ?? artifacts.error
  if (!data) return null
  return (
    <div className="agent-page">
      <PageHeader title={t('Agent workspace')} eyebrow="GOALS & TOOLS">
        <Link className="button secondary" to="/inbox">
          <MessageSquare size={16} />
          {t('Open chat')}
        </Link>
        <span className={`agent-worker ${data.settings.worker_online ? '' : 'offline'}`}>
          <span className="connection-dot" />
          {t(data.settings.worker_online ? 'Agent worker online' : 'Agent worker offline')}
        </span>
      </PageHeader>
      <div className="agent-view-tabs" role="tablist" aria-label={t('Agent views')}>
        {[
          ['runs', 'Agent runs'],
          ['tools', 'Tools and devices'],
          ['artifacts', 'Work artifacts'],
        ].map(([value, label]) => (
          <button
            key={value}
            role="tab"
            aria-selected={tab === value}
            onClick={() => setParams({ view: value, ...(selectedId ? { run: selectedId } : {}) })}
          >
            {t(label)}
            {value === 'artifacts' && <span>{artifacts.data?.length ?? 0}</span>}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="inline-error">
          {t(error.message)}
        </p>
      )}
      {data.settings.provider.name === 'DemoProvider' && (
        <p className="agent-run-warning" role="status">
          {t(
            'Offline rules demo: this mode only creates a labeled demonstration artifact after approval. It does not research, book, order, install software or call a model.',
          )}
        </p>
      )}
      {tab === 'runs' && (
        <div className="agent-workbench">
          <aside className="agent-sidebar">
            <form
              className="agent-goal-form"
              onSubmit={async (event) => {
                event.preventDefault()
                if (!goal.trim() || !allowedTools.length) return
                if (
                  await execute(async () => {
                    const created = await api<AgentRun>('/api/agent/runs', 'POST', {
                      goal: goal.trim(),
                      allowed_tools: allowedTools,
                      max_steps: maxSteps,
                      allow_external: consent,
                      auto_readonly: autoReadonly,
                    })
                    setParams({ view: 'runs', run: created.id })
                  }, 'Agent run started.')
                ) {
                  setGoal('')
                  setConsent(false)
                }
              }}
            >
              <h2>{t('New goal')}</h2>
              <label>
                {t('What should the Agent accomplish?')}
                <textarea
                  required
                  maxLength={10000}
                  value={goal}
                  placeholder={t('Describe the result you need, not just a task to remember.')}
                  onChange={(event) => setGoal(event.target.value)}
                />
              </label>
              <div className="agent-templates">
                {templates.map((template) => (
                  <button
                    key={template.label}
                    type="button"
                    className="text-button"
                    onClick={() => {
                      setGoal(t(template.goal))
                      setSelectedTools(template.tools)
                    }}
                  >
                    <template.icon size={15} />
                    {t(template.label)}
                  </button>
                ))}
              </div>
              <p className="agent-selected-tools" aria-label={t('Selected tools')}>
                {allowedTools
                  .map((name) =>
                    t(catalog.data?.tools.find((tool) => tool.name === name)?.label ?? name),
                  )
                  .join(' · ')}
              </p>
              <details className="agent-permissions">
                <summary>
                  {t('Allowed tools for this goal')} ({allowedTools.length})
                </summary>
                <div className="agent-tool-choices">
                  {catalog.data?.tools.map((tool) => (
                    <label key={tool.name} title={t(tool.description)}>
                      <input
                        type="checkbox"
                        disabled={!tool.available}
                        checked={selectedTools.includes(tool.name) && tool.available}
                        onChange={(event) =>
                          setSelectedTools((current) =>
                            event.target.checked
                              ? [...current, tool.name]
                              : current.filter((name) => name !== tool.name),
                          )
                        }
                      />
                      <span>
                        {t(tool.label)}
                        {!tool.available && (
                          <small>{t('Connection or server setup required')}</small>
                        )}
                      </span>
                      {tool.read_only && <span className="agent-readonly">{t('Read only')}</span>}
                    </label>
                  ))}
                </div>
              </details>
              <label>
                {t('Total step limit')}
                <input
                  type="number"
                  required
                  min={2}
                  max={24}
                  value={maxSteps}
                  onChange={(event) => setMaxSteps(Number(event.target.value))}
                />
              </label>
              <label className="consent">
                <input
                  type="checkbox"
                  checked={autoReadonly}
                  onChange={(event) => setAutoReadonly(event.target.checked)}
                />
                <span>
                  {t(
                    'Allow selected read-only tools to run automatically for this goal. Search queries may leave this workspace. Device actions still require approval.',
                  )}
                </span>
              </label>
              {catalog.data?.model_external && (
                <label className="consent">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(event) => setConsent(event.target.checked)}
                  />
                  <span>
                    {t(
                      'Allow this goal, clarifications, connection metadata and tool results to be shared with the configured model. Agent calls may incur provider charges.',
                    )}
                  </span>
                </label>
              )}
              {!catalog.data?.model_ready && (
                <Link className="agent-setup-link" to="/guide">
                  <Plug size={15} />
                  {t('Connect an Agent-compatible model')}
                  <ArrowRight size={15} />
                </Link>
              )}
              {!data.settings.worker_online && (
                <p className="field-help">
                  {t('The worker is offline. Runs remain queued until it reconnects.')}
                </p>
              )}
              <button
                className="button agent-start"
                disabled={
                  busy ||
                  !goal.trim() ||
                  !allowedTools.length ||
                  !catalog.data?.model_ready ||
                  (catalog.data.model_external && !consent)
                }
              >
                <Play size={16} />
                {t('Start Agent')}
              </button>
            </form>
            <section className="agent-run-list" aria-label={t('Recent Agent runs')}>
              <h2>{t('Recent Agent runs')}</h2>
              {runs.data?.map((item) => (
                <button
                  key={item.id}
                  className={selectedId === item.id ? 'selected' : ''}
                  onClick={() => setParams({ view: 'runs', run: item.id })}
                >
                  <strong>{item.goal}</strong>
                  <span>
                    {t(runLabels[item.status])}
                    <small>
                      {item.steps}/{item.max_steps}
                    </small>
                  </span>
                </button>
              ))}
            </section>
          </aside>
          <section className="agent-run-detail" aria-label={t('Agent execution')}>
            {!run ? (
              <div className="agent-idle">
                <img
                  src="/workspace.png"
                  alt={t('Illustration of a notebook and a plant on a sunlit desk')}
                />
                <EmptyState title={t('No Agent run selected')} icon={Bot} />
              </div>
            ) : (
              <>
                <header className="agent-run-heading">
                  <div>
                    <span className={`agent-run-state state-${run.status}`}>{t(statusLabel)}</span>
                    <h2>{run.goal}</h2>
                    <p>
                      {t('Steps {{used}} of {{limit}}', { used: run.steps, limit: run.max_steps })}{' '}
                      · {t('Authorization expires')} {formatDateTime(run.expires_at * 1000)}
                    </p>
                  </div>
                  <div className="row-actions">
                    {['queued', 'planning', 'waiting_approval'].includes(run.status) && (
                      <IconButton
                        icon={Pause}
                        label={t('Pause Agent')}
                        disabled={busy}
                        onClick={() =>
                          void execute(
                            () => api(`/api/agent/runs/${run.id}/pause`, 'POST'),
                            'Agent paused.',
                          )
                        }
                      />
                    )}
                    {['paused', 'needs_input'].includes(run.status) && (
                      <button
                        className="button secondary"
                        disabled={busy}
                        onClick={() => setContinuing(true)}
                      >
                        <Play size={16} />
                        {t('Continue Agent run')}
                      </button>
                    )}
                    {!['completed', 'cancelled'].includes(run.status) && (
                      <IconButton
                        icon={X}
                        label={t('Stop Agent')}
                        disabled={busy}
                        onClick={() =>
                          void execute(
                            () => api(`/api/agent/runs/${run.id}/cancel`, 'POST'),
                            'Agent stopped.',
                          )
                        }
                      />
                    )}
                  </div>
                </header>
                {run.error && (
                  <p className="agent-run-warning" role="alert">
                    {t(run.error)}
                  </p>
                )}
                {run.status === 'planning' && (
                  <p className="agent-planning" role="status">
                    <Bot size={18} />
                    {t('Reading results and choosing the next step...')}
                  </p>
                )}
                <ol className="agent-timeline">
                  {run.steps_history?.map((step) => (
                    <li className={`agent-step decision-${step.decision}`} key={step.id}>
                      <span className="agent-step-mark">
                        {step.decision === 'finish' ? <Check size={16} /> : step.ordinal}
                      </span>
                      <div className="agent-step-body">
                        <div className="agent-step-meta">
                          <strong>
                            {t(
                              {
                                act: 'Tool proposal',
                                finish: 'Agent result',
                                ask_user: 'Question for you',
                                user: 'Your clarification',
                              }[step.decision],
                            )}
                          </strong>
                          <time>{formatDateTime(step.created_at)}</time>
                        </div>
                        <p className="agent-step-message">{step.message}</p>
                        {step.action && <ActionCard action={step.action} />}
                      </div>
                    </li>
                  ))}
                </ol>
                {run.status === 'completed' && (
                  <div className="agent-completion">
                    <Check size={20} />
                    <span>
                      {t('Run finished. Review the tool results for what actually happened.')}
                    </span>
                  </div>
                )}
                {run.status === 'cancelled' && (
                  <p className="field-help">
                    {t(
                      'No further Agent steps will run. External actions already started may still finish.',
                    )}
                  </p>
                )}
                {artifacts.data?.some((item) => item.agent_run_id === run.id) && (
                  <div className="agent-artifact-links">
                    {artifacts.data
                      .filter((item) => item.agent_run_id === run.id)
                      .map((item) => (
                        <button
                          key={item.id}
                          className="button secondary"
                          onClick={() =>
                            void execute(async () =>
                              setArtifact(await api<WorkArtifact>(`/api/artifacts/${item.id}`)),
                            )
                          }
                        >
                          <FileText size={16} />
                          {item.title}
                        </button>
                      ))}
                  </div>
                )}
              </>
            )}
          </section>
        </div>
      )}
      {tab === 'tools' && (
        <div className="agent-tools-view">
          <section>
            <div className="section-heading">
              <h2>{t('Tool capabilities')}</h2>
              <Link className="text-button" to="/settings">
                {t('Connections')}
                <ArrowRight size={15} />
              </Link>
            </div>
            <div className="agent-tool-catalog">
              {catalog.data?.tools.map((tool) => (
                <article key={tool.name}>
                  <span className={`agent-tool-indicator ${tool.available ? 'available' : ''}`}>
                    <ShieldCheck size={20} />
                  </span>
                  <div>
                    <h3>{t(tool.label)}</h3>
                    <p>{t(tool.description)}</p>
                    <small>{t(tool.read_only ? 'Read only' : 'Exact approval required')}</small>
                  </div>
                  <span className="agent-tool-state">
                    {t(tool.available ? 'Tool available' : 'Connection or server setup required')}
                  </span>
                </article>
              ))}
            </div>
          </section>
          <DeviceConnections />
        </div>
      )}
      {tab === 'artifacts' && (
        <section className="agent-artifacts">
          <h2>{t('Work artifacts')}</h2>
          {artifacts.data?.length ? (
            artifacts.data.map((item) => (
              <article key={item.id}>
                <FileText size={22} />
                <div>
                  <h3>{item.title}</h3>
                  <p>
                    {formatDateTime(item.created_at)} ·{' '}
                    {t('{{count}} source links', { count: item.sources.length })}
                  </p>
                </div>
                <button
                  className="button secondary"
                  onClick={() =>
                    void execute(async () =>
                      setArtifact(await api<WorkArtifact>(`/api/artifacts/${item.id}`)),
                    )
                  }
                >
                  {t('Open artifact')}
                  <ArrowRight size={15} />
                </button>
              </article>
            ))
          ) : (
            <EmptyState title={t('No saved artifacts yet')} icon={FileText} />
          )}
        </section>
      )}
      {continuing && run && (
        <ContinueRun
          run={run}
          external={catalog.data?.model_external ?? true}
          onClose={() => setContinuing(false)}
        />
      )}
      {artifact && <ArtifactViewer artifact={artifact} onClose={() => setArtifact(null)} />}
    </div>
  )
}

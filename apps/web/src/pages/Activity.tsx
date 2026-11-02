import { useState } from 'react'
import { Activity as ActivityIcon, Clock3, ShieldCheck } from 'lucide-react'
import { ActionCard } from '../components/ActionCard'
import { AutomationList } from '../components/AutomationControls'
import { EmptyState, PageHeader } from '../components/ui'
import { formatTime } from '../api'
import { useWorkspace } from '../useWorkspace'

export function Activity() {
  const { data } = useWorkspace()
  const [filter, setFilter] = useState('all')
  if (!data) return null
  const actions = data.actions.filter((action) => filter === 'all' || action.status === filter)
  return (
    <>
      <PageHeader title="Nothing behind the scenes." eyebrow="ACTIVITY & APPROVALS">
        <span className="subtle-label">
          <ShieldCheck size={14} />
          Audit trail
        </span>
      </PageHeader>
      <AutomationList />
      <div className="activity-grid">
        <section>
          <div className="list-toolbar">
            <div className="segmented" role="tablist" aria-label="Action status">
              {[
                ['all', 'All actions'],
                ['pending', 'Needs approval'],
                ['succeeded', 'Completed'],
              ].map(([value, label]) => (
                <button
                  key={value}
                  role="tab"
                  aria-selected={filter === value}
                  onClick={() => setFilter(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="action-list">
            {actions.map((action) => (
              <ActionCard key={action.id} action={action} />
            ))}
          </div>
          {!actions.length && <EmptyState title="All quiet here." icon={ActivityIcon} />}
        </section>
        <aside className="audit-section">
          <div className="section-heading">
            <h2>Workspace history</h2>
            <Clock3 size={17} />
          </div>
          {data.audit.slice(0, 30).map((entry) => (
            <div className="audit-row" key={entry.id}>
              <span className="audit-dot" />
              <div>
                <strong>{entry.event.replaceAll('.', ' ').replaceAll('_', ' ')}</strong>
                <time>
                  {new Date(entry.created_at).toLocaleDateString('en', {
                    month: 'short',
                    day: 'numeric',
                  })}{' '}
                  / {formatTime(entry.created_at, data.plan.timezone)}
                </time>
              </div>
            </div>
          ))}
          {!data.audit.length && <p className="muted small">No activity yet.</p>}
        </aside>
      </div>
    </>
  )
}

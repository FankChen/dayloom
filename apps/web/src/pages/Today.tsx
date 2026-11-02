import { useTranslation } from 'react-i18next'
import {
  ArrowRight,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Leaf,
  Plus,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, formatDay, formatTime } from '../api'
import { EmptyState, IconButton, PageHeader } from '../components/ui'
import { useWorkspace } from '../useWorkspace'
import { GuideWelcome } from './Guide'

export function Today() {
  const { t } = useTranslation()

  const { data, busy, execute, setSelectedDay } = useWorkspace()
  if (!data) return null
  const { plan, tasks, actions, settings } = data
  const completed = tasks.filter((task) => task.status === 'done').length
  const pending = actions.filter((action) => action.status === 'pending').length
  const timeline = [
    ...plan.items.map((item) => ({
      id: item.task_id,
      title: item.title,
      start: item.start,
      end: item.end,
      kind: 'focus',
    })),
    ...plan.calendar.map((event) => ({ ...event, kind: 'calendar' })),
  ].sort((first, second) => first.start.localeCompare(second.start))
  function changeDay(offset: number) {
    const day = new Date(`${plan.day}T12:00:00`)
    day.setDate(day.getDate() + offset)
    setSelectedDay(
      `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`,
    )
  }
  return (
    <>
      <GuideWelcome key={data.account.workspace_id} />
      <PageHeader
        title={t('A day with intention.')}
        eyebrow={formatDay(plan.day, {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
          year: 'numeric',
        })}
      >
        <button
          className="button secondary"
          disabled={busy}
          onClick={() =>
            void execute(
              () =>
                api('/api/actions', 'POST', { tool: 'PrepareBrief', payload: { day: plan.day } }),
              'Brief queued for your approval.',
            )
          }
        >
          <Sparkles size={16} />
          {t('Daily brief')}
        </button>
        <Link to="/tasks?new=1" className="button">
          <Plus size={17} />
          {t('New task')}
        </Link>
      </PageHeader>
      <div className="overview-stats">
        <div>
          <span className="stat-label">{t('Your focus')}</span>
          <strong>
            {plan.items.length}
            <small>{t('priorities')}</small>
          </strong>
        </div>
        <div>
          <span className="stat-label">{t('Time set aside')}</span>
          <strong>
            {plan.planned_minutes}
            <small>{t('minutes')}</small>
          </strong>
        </div>
        <div>
          <span className="stat-label">{t('Progress')}</span>
          <strong>
            {completed}
            <small>{t('completed')}</small>
          </strong>
        </div>
        <div className="stat-approval">
          <span className="stat-label">{t('Needs your say')}</span>
          <Link to="/activity">
            <strong>
              {pending}
              <small>
                {t('approvals')} <ArrowRight size={14} />
              </small>
            </strong>
          </Link>
        </div>
      </div>
      <div className="today-grid">
        <section className="focus-section">
          <div className="section-heading">
            <h2>
              {t('Your next steps')} <span className="count">{plan.items.length}</span>
            </h2>
            <span className="muted small">
              {plan.planned_minutes} / {plan.capacity_minutes}
              {t('min')}
            </span>
          </div>
          <div
            className="capacity-bar"
            role="meter"
            aria-label={t('Planned time')}
            aria-valuenow={plan.planned_minutes}
            aria-valuemin={0}
            aria-valuemax={Math.max(1, plan.capacity_minutes)}
          >
            <span
              style={{
                width: `${plan.capacity_minutes ? (plan.planned_minutes / plan.capacity_minutes) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="focus-list">
            {plan.items.map((item, index) => (
              <article className={`focus-item priority-${item.priority}`} key={item.task_id}>
                <button
                  className="task-check"
                  aria-label={t('Complete {{title}}', { title: item.title })}
                  disabled={busy}
                  onClick={() => {
                    const task = tasks.find((candidate) => candidate.id === item.task_id)
                    if (!task) return
                    const { title, notes, priority, minutes, due_date, version } = task
                    void execute(
                      () =>
                        api(`/api/tasks/${task.id}`, 'PUT', {
                          title,
                          notes,
                          priority,
                          minutes,
                          due_date,
                          version,
                          status: 'done',
                        }),
                      'Task completed.',
                    )
                  }}
                >
                  <Check size={16} />
                </button>
                <div className="focus-body">
                  <div className="focus-meta">
                    <span className="focus-number">0{index + 1}</span>
                    <span className={`priority-label ${item.priority}`}>
                      {item.priority === 'high'
                        ? t('High priority')
                        : item.priority === 'low'
                          ? t('At your pace')
                          : t('On your list')}
                    </span>
                    <span className="duration">
                      <Clock3 size={13} />
                      {item.minutes}
                      {t('min')}
                    </span>
                  </div>
                  <Link to={`/tasks?edit=${item.task_id}`} className="focus-title">
                    {item.title}
                  </Link>
                  <p className="focus-reason">{t(item.reason)}</p>
                  <div className="focus-bottom">
                    <span>
                      {formatTime(item.start, plan.timezone)} -{' '}
                      {formatTime(item.end, plan.timezone)}
                    </span>
                    <span className="source-label">{t(item.source)}</span>
                  </div>
                </div>
              </article>
            ))}
            {!plan.items.length && (
              <EmptyState
                title={tasks.length ? t('A little breathing room.') : t('Your day starts here.')}
                icon={Leaf}
              >
                {tasks.length ? (
                  <button className="button secondary" onClick={() => changeDay(1)}>
                    {t('Look at tomorrow')} <ArrowRight size={15} />
                  </button>
                ) : (
                  <div className="empty-actions">
                    <Link className="button" to="/tasks?new=1">
                      <Plus size={16} />
                      {t('Add your first task')}
                    </Link>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        void execute(() => api('/api/demo', 'POST'), 'Sample workspace loaded.')
                      }
                    >
                      {t('Load sample workspace')}
                    </button>
                  </div>
                )}
              </EmptyState>
            )}
          </div>
          {plan.deadlines.length > 0 && (
            <section className="deadline-section">
              <div className="section-heading">
                <h2>{t('Coming due')}</h2>
                <CalendarDays size={17} />
              </div>
              {plan.deadlines.map((task) => (
                <Link
                  className="deadline-row"
                  to={`/tasks?edit=${task.task_id}`}
                  key={task.task_id}
                >
                  <span>{task.title}</span>
                  <span className={task.due_date <= plan.day ? 'text-coral' : 'muted'}>
                    {formatDay(task.due_date)}
                  </span>
                </Link>
              ))}
            </section>
          )}
          {plan.deferred.length > 0 && (
            <Link to="/tasks" className="remaining-link">
              <span>
                {plan.deferred.length} {t('more on your list')}
              </span>
              <ArrowRight size={17} />
            </Link>
          )}
        </section>
        <aside className="day-aside">
          <div className="workspace-photo">
            <img
              src="/workspace.png"
              alt={t('Illustration of a notebook and a plant on a sunlit desk')}
            />
            <span>{t('Personal workspace')}</span>
          </div>
          <div className="section-heading schedule-heading">
            <h2>{t('Your timeline')}</h2>
            <div className="date-controls">
              <IconButton
                icon={ChevronLeft}
                label={t('Previous day')}
                onClick={() => changeDay(-1)}
              />
              <input
                aria-label={t('Planning date')}
                type="date"
                value={plan.day}
                onChange={(event) => setSelectedDay(event.target.value)}
              />
              <IconButton icon={ChevronRight} label={t('Next day')} onClick={() => changeDay(1)} />
            </div>
          </div>
          <div className="timeline">
            {timeline.length ? (
              timeline.map((item) => (
                <div className={`timeline-row ${item.kind}`} key={item.id}>
                  <span className="timeline-time">{formatTime(item.start, plan.timezone)}</span>
                  <span className="timeline-marker" />
                  <div>
                    <strong>{item.title}</strong>
                    <span>
                      {formatTime(item.end, plan.timezone)}
                      {item.kind === 'calendar' ? t(' / Calendar') : t(' / Focus')}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="quiet-note">
                <CalendarDays size={20} />
                <span>{t('No scheduled blocks.')}</span>
              </div>
            )}
          </div>
          <div className="aside-footer">
            <span className={`connection-dot ${settings.worker_online ? 'online' : ''}`} />
            {settings.worker_online ? t('Worker connected') : t('Worker offline')}
            <Link to="/settings">
              {t('Connections')} <ArrowRight size={13} />
            </Link>
          </div>
        </aside>
      </div>
    </>
  )
}

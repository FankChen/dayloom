import { useTranslation } from 'react-i18next'
import { useDeferredValue, useState } from 'react'
import { Check, CircleCheck, Clock3, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { api, formatDay } from '../api'
import { ConfirmDelete, EmptyState, IconButton, Modal, PageHeader, Status } from '../components/ui'
import type { Priority, Task, TaskStatus } from '../types'
import { useWorkspace } from '../useWorkspace'

function TaskEditor({ task, onClose }: { task?: Task; onClose: () => void }) {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const [draft, setDraft] = useState({
    title: task?.title ?? '',
    notes: task?.notes ?? '',
    priority: task?.priority ?? ('normal' as Priority),
    minutes: task?.minutes ?? 30,
    due_date: task?.due_date ?? '',
    status: task?.status ?? ('ready' as TaskStatus),
    version: task?.version,
  })
  return (
    <Modal title={task ? t('Edit task') : t('New task')} onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          const payload = {
            title: draft.title,
            notes: draft.notes,
            priority: draft.priority,
            minutes: draft.minutes,
            due_date: draft.due_date || null,
            ...(task ? { status: draft.status, version: draft.version } : {}),
          }
          if (
            await execute(
              () =>
                api(task ? `/api/tasks/${task.id}` : '/api/tasks', task ? 'PUT' : 'POST', payload),
              task ? 'Task updated.' : 'Task added.',
            )
          )
            onClose()
        }}
      >
        <label>
          {t('Task title')}
          <input
            autoFocus
            required
            maxLength={200}
            value={draft.title}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />
        </label>
        <label>
          {t('Notes')}
          <textarea
            maxLength={5000}
            value={draft.notes}
            onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
          />
        </label>
        <div className="form-grid">
          <label>
            {t('Priority')}
            <select
              value={draft.priority}
              onChange={(event) => setDraft({ ...draft, priority: event.target.value as Priority })}
            >
              <option value="high">{t('High')}</option>
              <option value="normal">{t('Normal')}</option>
              <option value="low">{t('Low')}</option>
            </select>
          </label>
          <label>
            {t('Estimate (minutes)')}
            <input
              type="number"
              min={5}
              max={480}
              step={5}
              required
              value={draft.minutes}
              onChange={(event) => setDraft({ ...draft, minutes: Number(event.target.value) })}
            />
          </label>
        </div>
        <div className="form-grid">
          <label>
            {t('Due date')}
            <input
              type="date"
              value={draft.due_date}
              onChange={(event) => setDraft({ ...draft, due_date: event.target.value })}
            />
          </label>
          {task && (
            <label>
              {t('Status')}
              <select
                value={draft.status}
                onChange={(event) =>
                  setDraft({ ...draft, status: event.target.value as TaskStatus })
                }
              >
                <option value="ready">{t('Ready')}</option>
                <option value="doing">{t('In progress')}</option>
                <option value="blocked">{t('Blocked')}</option>
                <option value="done">{t('Done')}</option>
              </select>
            </label>
          )}
        </div>
        <div className="form-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button type="submit" className="button" disabled={busy}>
            {task ? t('Save changes') : t('Create task')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function Tasks() {
  const { t } = useTranslation()

  const { data, busy, execute } = useWorkspace()
  const [params, setParams] = useSearchParams()
  const [filter, setFilter] = useState('active')
  const [search, setSearch] = useState('')
  const [removing, setRemoving] = useState<Task | null>(null)
  const deferredSearch = useDeferredValue(search)
  if (!data) return null
  const editing = data.tasks.find((task) => task.id === params.get('edit'))
  const filtered = data.tasks.filter(
    (task) =>
      (filter === 'all' || (filter === 'done' ? task.status === 'done' : task.status !== 'done')) &&
      `${task.title} ${task.notes}`.toLowerCase().includes(deferredSearch.toLowerCase()),
  )
  return (
    <>
      <PageHeader title={t('Room for the important things.')} eyebrow="YOUR TASKS">
        <button className="button" onClick={() => setParams({ new: '1' })}>
          <Plus size={16} />
          {t('New task')}
        </button>
      </PageHeader>
      <div className="list-toolbar">
        <div className="segmented" role="tablist" aria-label={t('Task status')}>
          {[
            ['active', 'Active'],
            ['done', 'Completed'],
            ['all', 'All tasks'],
          ].map(([value, label]) => (
            <button
              key={value}
              role="tab"
              aria-selected={filter === value}
              onClick={() => setFilter(value)}
            >
              {t(label)}
            </button>
          ))}
        </div>
        <div className="search-field">
          <Search size={16} />
          <input
            type="search"
            aria-label={t('Search tasks')}
            placeholder={t('Search tasks')}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </div>
      <div className="task-list">
        {filtered.map((task) => (
          <article
            className={`task-row ${task.status === 'done' ? 'completed' : ''}`}
            key={task.id}
          >
            <button
              className={`task-check ${task.status === 'done' ? 'checked' : ''}`}
              disabled={busy}
              aria-label={t(task.status === 'done' ? 'Reopen {{title}}' : 'Complete {{title}}', {
                title: task.title,
              })}
              onClick={() => {
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
                      status: task.status === 'done' ? 'ready' : 'done',
                    }),
                  task.status === 'done' ? 'Task reopened.' : 'Task completed.',
                )
              }}
            >
              <Check size={14} />
            </button>
            <div className="task-row-main">
              <button className="task-title-button" onClick={() => setParams({ edit: task.id })}>
                {task.title}
              </button>
              {task.notes && <p>{task.notes}</p>}
              <div className="task-row-meta">
                <Status value={task.status} />
                <span>
                  <Clock3 size={12} />
                  {task.minutes}
                  {t('min')}
                </span>
                {task.due_date && (
                  <span
                    className={
                      task.due_date <= data.plan.day && task.status !== 'done' ? 'text-coral' : ''
                    }
                  >
                    {t('Due')} {formatDay(task.due_date)}
                  </span>
                )}
                <span className={`priority-label ${task.priority}`}>
                  {t(task.priority)} {t('priority')}
                </span>
              </div>
            </div>
            <div className="row-actions">
              <IconButton
                icon={Pencil}
                label={t('Edit {{title}}', { title: task.title })}
                onClick={() => setParams({ edit: task.id })}
              />
              <IconButton
                icon={Trash2}
                label={t('Delete {{title}}', { title: task.title })}
                onClick={() => setRemoving(task)}
              />
            </div>
          </article>
        ))}
      </div>
      {!filtered.length && (
        <EmptyState
          title={
            search
              ? t('Nothing matches just yet.')
              : filter === 'done'
                ? t('A fresh start.')
                : t('Nothing on your list.')
          }
          icon={CircleCheck}
        >
          {!search && filter !== 'done' && (
            <button className="button secondary" onClick={() => setParams({ new: '1' })}>
              <Plus size={16} />
              {t('Add a task')}
            </button>
          )}
        </EmptyState>
      )}
      {(params.has('new') || editing) && (
        <TaskEditor key={editing?.id ?? 'new'} task={editing} onClose={() => setParams({})} />
      )}
      {removing && (
        <ConfirmDelete
          title={t('Delete this task?')}
          busy={busy}
          onClose={() => setRemoving(null)}
          onConfirm={() =>
            void execute(() => api(`/api/tasks/${removing.id}`, 'DELETE'), 'Task deleted.').then(
              (success) => {
                if (success) setRemoving(null)
              },
            )
          }
        />
      )}
    </>
  )
}

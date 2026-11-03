import { useState } from 'react'
import { Check, Undo2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { api } from '../api'
import { useWorkspace } from '../useWorkspace'
import { Modal } from './ui'

export function TaskStatusControl({ taskId }: { taskId: string }) {
  const { t } = useTranslation()
  const { data, busy, execute } = useWorkspace()
  const [confirming, setConfirming] = useState(false)
  const task = data?.tasks.find((candidate) => candidate.id === taskId)
  if (!task) return null
  const reopening = task.status === 'done'
  const label = t(reopening ? 'Reopen {{title}}' : 'Complete {{title}}', { title: task.title })
  function changeStatus() {
    if (!task) return Promise.resolve(false)
    const { title, notes, priority, minutes, due_date, version } = task
    return execute(
      () =>
        api(`/api/tasks/${task.id}`, 'PUT', {
          title,
          notes,
          priority,
          minutes,
          due_date,
          version,
          status: reopening ? 'ready' : 'done',
        }),
      reopening ? 'Task reopened.' : 'Task completed.',
    )
  }
  return (
    <>
      <button
        className={reopening ? 'button secondary compact' : 'task-check'}
        disabled={busy}
        aria-label={label}
        title={label}
        onClick={() => {
          if (reopening) void changeStatus()
          else setConfirming(true)
        }}
      >
        {reopening ? <Undo2 size={16} /> : <Check size={14} />}
        {reopening && t('Reopen task')}
      </button>
      {confirming && !reopening && (
        <Modal title={t('Complete this task?')} onClose={() => setConfirming(false)}>
          <p className="muted">{task.title}</p>
          <div className="form-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setConfirming(false)}
            >
              {t('Cancel')}
            </button>
            <button
              className="button"
              disabled={busy}
              onClick={() =>
                void changeStatus().then((success) => {
                  if (success) setConfirming(false)
                })
              }
            >
              <Check size={16} />
              {t('Complete task')}
            </button>
          </div>
        </Modal>
      )}
    </>
  )
}

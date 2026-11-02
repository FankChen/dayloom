import { useTranslation } from 'react-i18next'
import { useDeferredValue, useState } from 'react'
import { Flag, Leaf, Lightbulb, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { api, formatDay } from '../api'
import { ConfirmDelete, EmptyState, IconButton, Modal, PageHeader } from '../components/ui'
import type { Memory, MemoryCategory } from '../types'
import { useWorkspace } from '../useWorkspace'

function MemoryEditor({ memory, onClose }: { memory?: Memory; onClose: () => void }) {
  const { t } = useTranslation()

  const { busy, execute } = useWorkspace()
  const [draft, setDraft] = useState({
    content: memory?.content ?? '',
    category: memory?.category ?? ('preference' as MemoryCategory),
    expires_on: memory?.expires_on ?? '',
    version: memory?.version,
  })
  return (
    <Modal title={memory ? t('Edit memory') : t('New memory')} onClose={onClose}>
      <form
        onSubmit={async (event) => {
          event.preventDefault()
          const payload = {
            content: draft.content,
            category: draft.category,
            expires_on: draft.expires_on || null,
            ...(memory ? { version: draft.version } : {}),
          }
          if (
            await execute(
              () =>
                api(
                  memory ? `/api/memories/${memory.id}` : '/api/memories',
                  memory ? 'PUT' : 'POST',
                  payload,
                ),
              'Memory saved.',
            )
          )
            onClose()
        }}
      >
        <label>
          {t('Memory')}
          <textarea
            autoFocus
            required
            maxLength={3000}
            value={draft.content}
            onChange={(event) => setDraft({ ...draft, content: event.target.value })}
          />
        </label>
        <div className="form-grid">
          <label>
            {t('Category')}
            <select
              value={draft.category}
              onChange={(event) =>
                setDraft({ ...draft, category: event.target.value as MemoryCategory })
              }
            >
              <option value="preference">{t('Preference')}</option>
              <option value="goal">{t('Goal')}</option>
              <option value="fact">{t('Fact')}</option>
              <option value="context">{t('Temporary context')}</option>
            </select>
          </label>
          <label>
            {t('Expires on')}
            <input
              type="date"
              value={draft.expires_on}
              onChange={(event) => setDraft({ ...draft, expires_on: event.target.value })}
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="button secondary" type="button" onClick={onClose}>
            {t('Cancel')}
          </button>
          <button className="button" type="submit" disabled={busy}>
            {t('Save memory')}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function Memories() {
  const { t } = useTranslation()

  const { data, busy, execute } = useWorkspace()
  const [editing, setEditing] = useState<Memory | 'new' | null>(null)
  const [removing, setRemoving] = useState<Memory | null>(null)
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)
  const [category, setCategory] = useState('all')
  if (!data) return null
  const memories = data.memories.filter(
    (memory) =>
      (category === 'all' || memory.category === category) &&
      memory.content.toLowerCase().includes(deferredSearch.toLowerCase()),
  )
  return (
    <>
      <PageHeader title={t('The things that make you, you.')} eyebrow="YOUR MEMORY">
        <button className="button" onClick={() => setEditing('new')}>
          <Plus size={16} />
          {t('New memory')}
        </button>
      </PageHeader>
      <div className="list-toolbar">
        <select
          className="category-select"
          aria-label={t('Memory category')}
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option value="all">{t('All memories')}</option>
          <option value="preference">{t('Preferences')}</option>
          <option value="goal">{t('Goals')}</option>
          <option value="fact">{t('Facts')}</option>
          <option value="context">{t('Temporary context')}</option>
        </select>
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label={t('Search memories')}
            type="search"
            placeholder={t('Search memories')}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </div>
      <div className="memory-grid">
        {memories.map((memory) => {
          const expired = Boolean(memory.expires_on && memory.expires_on < data.plan.day)
          const Icon =
            memory.category === 'goal' ? Flag : memory.category === 'fact' ? Lightbulb : Leaf
          return (
            <article className={`memory-item ${expired ? 'expired' : ''}`} key={memory.id}>
              <div className="memory-heading">
                <span className={`memory-category category-${memory.category}`}>
                  <Icon size={16} />
                  {t(memory.category)}
                </span>
                <div className="row-actions">
                  <IconButton
                    icon={Pencil}
                    label={t('Edit memory')}
                    onClick={() => setEditing(memory)}
                  />
                  <IconButton
                    icon={Trash2}
                    label={t('Delete memory')}
                    onClick={() => setRemoving(memory)}
                  />
                </div>
              </div>
              <p>{memory.content}</p>
              <div className="memory-footer">
                <span>{t(memory.source)}</span>
                {memory.expires_on && (
                  <span>
                    {expired ? t('Expired') : t('Until')} {formatDay(memory.expires_on)}
                  </span>
                )}
              </div>
            </article>
          )
        })}
      </div>
      {!memories.length && (
        <EmptyState
          title={search ? t('No matching memories.') : t('A little more like you.')}
          icon={Leaf}
        >
          <button className="button secondary" onClick={() => setEditing('new')}>
            <Plus size={16} />
            {t('Add a memory')}
          </button>
        </EmptyState>
      )}
      {editing && (
        <MemoryEditor
          memory={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
      {removing && (
        <ConfirmDelete
          title={t('Delete this memory?')}
          busy={busy}
          onClose={() => setRemoving(null)}
          onConfirm={() =>
            void execute(
              () => api(`/api/memories/${removing.id}`, 'DELETE'),
              'Memory deleted. Original conversation history is unchanged.',
            ).then((success) => {
              if (success) setRemoving(null)
            })
          }
        />
      )}
    </>
  )
}

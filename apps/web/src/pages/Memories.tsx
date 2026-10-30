import { useDeferredValue, useState } from 'react'
import { Flag, Leaf, Lightbulb, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { api, formatDay } from '../api'
import { ConfirmDelete, EmptyState, IconButton, Modal, PageHeader } from '../components/ui'
import type { Memory, MemoryCategory } from '../types'
import { useWorkspace } from '../useWorkspace'

function MemoryEditor({ memory, onClose }: { memory?: Memory; onClose: () => void }) {
  const { busy, execute } = useWorkspace()
  const [draft, setDraft] = useState({
    content: memory?.content ?? '',
    category: memory?.category ?? ('preference' as MemoryCategory),
    expires_on: memory?.expires_on ?? '',
    version: memory?.version,
  })
  return (
    <Modal title={memory ? 'Edit memory' : 'New memory'} onClose={onClose}>
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
          Memory
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
            Category
            <select
              value={draft.category}
              onChange={(event) =>
                setDraft({ ...draft, category: event.target.value as MemoryCategory })
              }
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
              value={draft.expires_on}
              onChange={(event) => setDraft({ ...draft, expires_on: event.target.value })}
            />
          </label>
        </div>
        <div className="form-actions">
          <button className="button secondary" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="button" type="submit" disabled={busy}>
            Save memory
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function Memories() {
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
      <PageHeader title="The things that make you, you." eyebrow="YOUR MEMORY">
        <button className="button" onClick={() => setEditing('new')}>
          <Plus size={16} />
          New memory
        </button>
      </PageHeader>
      <div className="list-toolbar">
        <select
          className="category-select"
          aria-label="Memory category"
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option value="all">All memories</option>
          <option value="preference">Preferences</option>
          <option value="goal">Goals</option>
          <option value="fact">Facts</option>
          <option value="context">Temporary context</option>
        </select>
        <div className="search-field">
          <Search size={16} />
          <input
            aria-label="Search memories"
            type="search"
            placeholder="Search memories"
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
                  {memory.category}
                </span>
                <div className="row-actions">
                  <IconButton
                    icon={Pencil}
                    label="Edit memory"
                    onClick={() => setEditing(memory)}
                  />
                  <IconButton
                    icon={Trash2}
                    label="Delete memory"
                    onClick={() => setRemoving(memory)}
                  />
                </div>
              </div>
              <p>{memory.content}</p>
              <div className="memory-footer">
                <span>{memory.source}</span>
                {memory.expires_on && (
                  <span>
                    {expired ? 'Expired' : 'Until'} {formatDay(memory.expires_on)}
                  </span>
                )}
              </div>
            </article>
          )
        })}
      </div>
      {!memories.length && (
        <EmptyState
          title={search ? 'No matching memories.' : 'A little more like you.'}
          icon={Leaf}
        >
          <button className="button secondary" onClick={() => setEditing('new')}>
            <Plus size={16} />
            Add a memory
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
          title="Delete this memory?"
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

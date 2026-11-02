import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUp, Command, LoaderCircle, MessageSquare, ShieldCheck } from 'lucide-react'
import { api, formatTime } from '../api'
import { ActionCard } from '../components/ActionCard'
import { EmptyState, PageHeader } from '../components/ui'
import { useWorkspace } from '../useWorkspace'

export function Inbox() {
  const { data, busy, execute } = useWorkspace()
  const [content, setContent] = useState('')
  const [allowExternal, setAllowExternal] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)
  const messageCount = data?.messages.length ?? 0
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [messageCount])
  if (!data) return null
  const pending = data.actions.filter((action) => action.status === 'pending')
  return (
    <>
      <PageHeader title="A place to think out loud." eyebrow="YOUR INBOX">
        <span className="subtle-label">
          <ShieldCheck size={14} />
          Approval before action
        </span>
      </PageHeader>
      <div className="inbox-grid">
        <section className="conversation">
          <div className="messages" aria-live="polite" aria-label="Conversation">
            {data.messages.length === 0 && (
              <EmptyState title="What's on your mind?" icon={MessageSquare} />
            )}
            {data.messages.map((message) => (
              <article className={`message message-${message.role}`} key={message.id}>
                <div className="message-author">
                  {message.role === 'assistant' ? (
                    <>
                      <Command size={15} />
                      Dayloom
                    </>
                  ) : (
                    <>
                      <span className="user-initial">Y</span>You
                    </>
                  )}
                  <time>{formatTime(message.created_at, data.plan.timezone)}</time>
                </div>
                <p>{message.content}</p>
              </article>
            ))}
            {busy && (
              <div className="thinking">
                <LoaderCircle size={15} className="spin" />
                Working...
              </div>
            )}
            <div ref={bottom} />
          </div>
          <form
            className="composer"
            onSubmit={async (event) => {
              event.preventDefault()
              if (!content.trim()) return
              if (
                await execute(() =>
                  api('/api/chat', 'POST', {
                    content: content.trim(),
                    allow_external: allowExternal,
                  }),
                )
              )
                setContent('')
            }}
          >
            <textarea
              aria-label="Message Dayloom"
              placeholder="What's on your mind?"
              value={content}
              maxLength={10000}
              required
              onChange={(event) => setContent(event.target.value)}
            />
            <div className="composer-footer">
              <span>
                {!data.settings.provider.configured ? (
                  <Link to="/settings">Connect a model</Link>
                ) : data.settings.provider.external ? (
                  data.settings.provider.model
                ) : (
                  'Offline demo'
                )}
              </span>
              <button
                className="send-button"
                type="submit"
                aria-label="Send message"
                disabled={
                  busy ||
                  !content.trim() ||
                  !data.settings.provider.configured ||
                  (data.settings.provider.external && !allowExternal)
                }
              >
                <ArrowUp size={19} />
              </button>
            </div>
            {data.settings.provider.external && data.settings.provider.configured && (
              <label className="consent">
                <input
                  type="checkbox"
                  checked={allowExternal}
                  onChange={(event) => setAllowExternal(event.target.checked)}
                />
                <span>
                  Share this message, recent conversation, task titles, active memories and
                  connected sender addresses with {data.settings.provider.model}.
                </span>
              </label>
            )}
          </form>
        </section>
        <aside className="suggestions">
          <div className="section-heading">
            <h2>
              For your review <span className="count">{pending.length}</span>
            </h2>
          </div>
          {pending.length ? (
            pending.map((action) => <ActionCard key={action.id} action={action} />)
          ) : (
            <div className="quiet-note">
              <ShieldCheck size={20} />
              <span>Nothing awaiting approval.</span>
            </div>
          )}
        </aside>
      </div>
    </>
  )
}

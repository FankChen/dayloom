import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Inbox, X, type LucideIcon } from 'lucide-react'

export function IconButton({
  icon: Icon,
  label,
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; label: string }) {
  return (
    <button
      type="button"
      className={`icon-button ${className}`}
      title={label}
      aria-label={label}
      {...props}
    >
      <Icon size={18} />
    </button>
  )
}
export function PageHeader({
  title,
  eyebrow,
  children,
}: {
  title: string
  eyebrow: string
  children?: ReactNode
}) {
  return (
    <header className="page-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      <div className="header-actions">{children}</div>
    </header>
  )
}
export function EmptyState({
  title,
  icon: Icon = Inbox,
  children,
}: {
  title: string
  icon?: LucideIcon
  children?: ReactNode
}) {
  return (
    <div className="empty-state">
      <Icon size={28} strokeWidth={1.4} />
      <h3>{title}</h3>
      {children}
    </div>
  )
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => {
      element?.close()
    }
  }, [])
  return (
    <dialog ref={dialog} className="modal" aria-label={title} onCancel={onClose}>
      <div className="modal-heading">
        <h2>{title}</h2>
        <IconButton icon={X} label="Close dialog" onClick={onClose} />
      </div>
      {children}
    </dialog>
  )
}
export function Status({ value }: { value: string }) {
  return (
    <span className={`status status-${value}`}>
      <span className="status-dot" />
      {value.replaceAll('_', ' ')}
    </span>
  )
}
export function ConfirmDelete({
  title,
  onClose,
  onConfirm,
  busy,
}: {
  title: string
  onClose: () => void
  onConfirm: () => void
  busy: boolean
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <p className="muted">This cannot be undone.</p>
      <div className="form-actions">
        <button className="button secondary" onClick={onClose}>
          Cancel
        </button>
        <button className="button danger" disabled={busy} onClick={onConfirm}>
          Delete
        </button>
      </div>
    </Modal>
  )
}

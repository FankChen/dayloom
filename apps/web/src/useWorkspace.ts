import { createContext, useContext } from 'react'
import type { Workspace } from './types'

export interface WorkspaceContextValue {
  data: Workspace | undefined
  loading: boolean
  error: Error | null
  busy: boolean
  notice: { text: string; error: boolean } | null
  clearNotice: () => void
  selectedDay: string
  setSelectedDay: (day: string) => void
  refresh: () => void
  execute: (operation: () => Promise<unknown>, success?: string) => Promise<boolean>
}

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (!context) throw new Error('Missing workspace provider')
  return context
}

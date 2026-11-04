import { useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from './api'
import type { Workspace } from './types'
import { WorkspaceContext, type WorkspaceContextValue } from './useWorkspace'

async function loadWorkspace(day: string): Promise<Workspace> {
  const [tasks, memories, messages, actions, audit, calendar, plan, settings, account] =
    await Promise.all([
      api<Workspace['tasks']>('/api/tasks'),
      api<Workspace['memories']>('/api/memories'),
      api<Workspace['messages']>('/api/messages'),
      api<Workspace['actions']>('/api/actions'),
      api<Workspace['audit']>('/api/audit'),
      api<Workspace['calendar']>('/api/calendar'),
      api<Workspace['plan']>(`/api/plan${day ? `?day=${day}` : ''}`),
      api<Workspace['settings']>('/api/settings'),
      api<Workspace['account']>('/api/auth/me'),
    ])
  return { tasks, memories, messages, actions, audit, calendar, plan, settings, account }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient()
  const [selectedDay, setSelectedDay] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<WorkspaceContextValue['notice']>(null)
  const query = useQuery({
    queryKey: ['workspace', selectedDay],
    queryFn: () => loadWorkspace(selectedDay),
    refetchInterval: 5000,
    staleTime: 3000,
    retry: false,
  })
  async function execute(operation: () => Promise<unknown>, success?: string) {
    setBusy(true)
    setNotice(null)
    try {
      await operation()
      await client.invalidateQueries({ queryKey: ['workspace'] })
      await client.invalidateQueries({ queryKey: ['agent'] })
      if (success) setNotice({ text: success, error: false })
      return true
    } catch (error) {
      setNotice({
        text: error instanceof Error ? error.message : 'Something went wrong.',
        error: true,
      })
      return false
    } finally {
      setBusy(false)
    }
  }
  return (
    <WorkspaceContext.Provider
      value={{
        data:
          query.error instanceof ApiError && query.error.status === 401 ? undefined : query.data,
        loading: query.isPending,
        error: query.error,
        busy,
        notice,
        clearNotice: () => setNotice(null),
        selectedDay,
        setSelectedDay,
        refresh: () => {
          void client.invalidateQueries({ queryKey: ['workspace'] })
          void client.invalidateQueries({ queryKey: ['agent'] })
        },
        execute,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export type TaskStatus = 'ready' | 'doing' | 'blocked' | 'done'
export type Priority = 'high' | 'normal' | 'low'
export type MemoryCategory = 'preference' | 'goal' | 'fact' | 'context'

export interface Task {
  id: string
  title: string
  notes: string
  status: TaskStatus
  priority: Priority
  minutes: number
  due_date: string | null
  source: string
  version: number
  created_at: string
  updated_at: string
}
export interface Memory {
  id: string
  content: string
  category: MemoryCategory
  source: string
  expires_on: string | null
  version: number
  updated_at: string
}
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  provider: string
  created_at: string
}
export interface Action {
  id: string
  agent_run_id?: string | null
  tool: string
  payload: Record<string, unknown>
  digest: string
  status:
    'pending' | 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled' | 'outcome_unknown'
  result: {
    kind: string
    title: string
    id?: string
    plan?: Plan
    text?: string
    url?: string
    sources?: { title: string; url: string; snippet: string }[] | string[]
    data?: unknown
    download_url?: string
    execution_location?: string
  } | null
  error: string | null
  attempts: number
  created_at: string
  updated_at: string
}
export interface CalendarEvent {
  id: string
  title: string
  start: string
  end: string
  source: string
  imported_at: string
}

export interface AgentTool {
  name: string
  label: string
  description: string
  input_schema: Record<string, unknown>
  read_only: boolean
  execution: string
  available: boolean
  connection_kind: string | null
}
export interface AgentCatalog {
  tools: AgentTool[]
  model_ready: boolean
  model_external: boolean
}
export interface AgentStep {
  id: string
  ordinal: number
  decision: 'act' | 'finish' | 'ask_user' | 'user'
  message: string
  created_at: string
  action: Action | null
}
export interface AgentRun {
  id: string
  goal: string
  status:
    | 'queued'
    | 'planning'
    | 'waiting_approval'
    | 'needs_input'
    | 'paused'
    | 'completed'
    | 'cancelled'
  allowed_tools: string[]
  auto_readonly: number
  allow_external: number
  steps: number
  max_steps: number
  expires_at: number
  summary: string
  error: string | null
  created_at: string
  updated_at: string
  steps_history?: AgentStep[]
}
export interface WorkArtifact {
  id: string
  title: string
  content?: string
  sources: string[]
  agent_run_id: string | null
  created_at: string
}
export interface DeviceConnection {
  id: string
  label: string
  version: number
  endpoint: string
  authorized_tools: string[]
  catalog: { name: string; description: string; input_schema: Record<string, unknown> }[]
}
export interface DeviceCatalog {
  connections: DeviceConnection[]
  allowed_servers: string[]
}
export interface PlanItem {
  task_id: string
  title: string
  start: string
  end: string
  minutes: number
  priority: Priority
  reason: string
  source: string
}
export interface Plan {
  day: string
  timezone: string
  items: PlanItem[]
  deferred: { task_id: string; title: string; reason: string }[]
  deadlines: { task_id: string; title: string; due_date: string }[]
  calendar: CalendarEvent[]
  available_minutes: number
  capacity_minutes: number
  planned_minutes: number
  strategy: string
}
export interface Preferences {
  timezone: string
  daily_minutes: number
  work_start: number
  work_end: number
  focus_count: number
}
export interface Settings {
  preferences: Preferences
  provider: {
    name: string | null
    label: string
    external: boolean
    model: string | null
    configured: boolean
    managed: 'server' | 'workspace'
    base_url?: string
    max_tokens?: number
    daily_limit?: number
    used_today?: number
    version?: number
  }
  worker_online: boolean
  tools: { name: string; label: string; automation_allowed: boolean }[]
}
export interface AuditEntry {
  id: string
  event: string
  entity_id: string
  details: Record<string, unknown>
  created_at: string
}
export interface Workspace {
  account: {
    mode: 'local' | 'oidc'
    name: string
    workspace_id: string
    session_id: string | null
  }
  tasks: Task[]
  memories: Memory[]
  messages: Message[]
  actions: Action[]
  audit: AuditEntry[]
  calendar: CalendarEvent[]
  plan: Plan
  settings: Settings
}

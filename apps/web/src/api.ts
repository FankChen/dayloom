export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export function saveAccessToken(token: string) {
  if (token) sessionStorage.setItem('dayloom-access', token)
  else sessionStorage.removeItem('dayloom-access')
}

export async function api<Result>(
  path: string,
  method = 'GET',
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<Result> {
  const token = sessionStorage.getItem('dayloom-access')
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...extraHeaders,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}))
    const detail =
      typeof failure.detail === 'string'
        ? failure.detail
        : 'Please check the entered values and try again.'
    throw new ApiError(detail, response.status)
  }
  if (response.status === 204) return undefined as Result
  return response.json() as Promise<Result>
}

export function formatTime(value: string, timezone?: string) {
  return new Intl.DateTimeFormat('en', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: timezone,
  }).format(new Date(value))
}

export function formatDay(value: string, options?: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat('en', options ?? { month: 'short', day: 'numeric' }).format(
    new Date(`${value}T12:00:00`),
  )
}

import { clearNativeSession, isNative, nativeSession, saveNativeSession } from './platform/native'
import i18n from './i18n'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
let refreshOperation: Promise<boolean> | undefined

async function refreshSession() {
  refreshOperation ??= (async () => {
    const stored = await nativeSession()
    if (isNative && !stored) return false
    const response = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', 'X-Dayloom-CSRF': '1' },
      body: JSON.stringify(stored ? { refresh_token: stored.refresh_token } : {}),
    })
    if (response.ok && isNative) await saveNativeSession(await response.json())
    if (response.status === 401 && isNative) await clearNativeSession()
    return response.ok
  })()
    .catch(() => false)
    .finally(() => {
      refreshOperation = undefined
    })
  return refreshOperation
}

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
  const legacyToken = sessionStorage.getItem('dayloom-access')
  const token = (await nativeSession())?.access_token ?? legacyToken
  const options: RequestInit = {
    method,
    credentials: 'include',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(method !== 'GET' ? { 'X-Dayloom-CSRF': '1' } : {}),
      ...extraHeaders,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  }
  let response = await fetch(`${baseUrl}${path}`, options)
  if (
    response.status === 401 &&
    (!legacyToken || isNative) &&
    !path.startsWith('/api/auth/') &&
    (await refreshSession())
  ) {
    if (isNative)
      options.headers = {
        ...options.headers,
        Authorization: `Bearer ${(await nativeSession())?.access_token ?? ''}`,
      }
    response = await fetch(`${baseUrl}${path}`, options)
  }
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
  return new Intl.DateTimeFormat(i18n.language, {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: timezone,
  }).format(new Date(value))
}

export function formatDay(value: string, options?: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat(
    i18n.language,
    options ?? { month: 'short', day: 'numeric' },
  ).format(new Date(`${value}T12:00:00`))
}

export function formatDateTime(value: string | number) {
  return new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(value),
  )
}

import { Capacitor, registerPlugin } from '@capacitor/core'
import { App } from '@capacitor/app'
import { Browser } from '@capacitor/browser'

export const isNative = Capacitor.isNativePlatform()
export interface CapturedNotification {
  id: string
  packageName: string
  title: string
  body: string
  capturedAt: number
}
interface NativeBridge {
  getSecret(options: { key: string }): Promise<{ value: string | null }>
  setSecret(options: { key: string; value: string }): Promise<void>
  removeSecret(options: { key: string }): Promise<void>
  notificationStatus(): Promise<{
    supported: boolean
    granted: boolean
    enabled: boolean
    packages: string[]
  }>
  notificationSources(): Promise<{ sources: { packageName: string }[] }>
  configureNotifications(options: { enabled: boolean; packages: string[] }): Promise<void>
  openNotificationAccess(): Promise<void>
  readNotifications(): Promise<{ events: CapturedNotification[] }>
  clearNotifications(): Promise<void>
}
export const NativeBridge = registerPlugin<NativeBridge>('DayloomNative')

interface Tokens {
  access_token: string
  refresh_token: string
  expires_in: number
}
let cached: Tokens | null | undefined
let processingTicket: string | undefined

export async function nativeSession() {
  if (!isNative) return null
  if (cached === undefined) {
    const stored = await NativeBridge.getSecret({ key: 'auth-session' })
    cached = stored.value ? (JSON.parse(stored.value) as Tokens) : null
  }
  return cached
}

export async function saveNativeSession(tokens: Tokens) {
  await NativeBridge.setSecret({ key: 'auth-session', value: JSON.stringify(tokens) })
  cached = tokens
}

export async function clearNativeSession() {
  if (!isNative) return
  cached = null
  await NativeBridge.removeSecret({ key: 'auth-session' })
  await NativeBridge.removeSecret({ key: 'login-verifier' })
  if (Capacitor.getPlatform() === 'android') {
    await NativeBridge.configureNotifications({ enabled: false, packages: [] })
    await NativeBridge.clearNotifications()
  }
}

function base64Url(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes))
    .replaceAll('+', '-')
    .replaceAll('/', '_')
    .replaceAll('=', '')
}

export async function signIn(loginUrl: string) {
  if (!isNative) {
    window.location.assign(loginUrl)
    return
  }
  const verifier = base64Url(crypto.getRandomValues(new Uint8Array(48)))
  await NativeBridge.setSecret({ key: 'login-verifier', value: verifier })
  const digest = new Uint8Array(
    await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)),
  )
  const target = new URL(loginUrl)
  if (target.protocol !== 'https:') throw new Error('Native login requires an HTTPS server.')
  target.searchParams.set('native_challenge', base64Url(digest))
  await Browser.open({ url: target.toString() })
}

export async function setupNativeAuthentication(baseUrl: string) {
  if (!isNative) return () => {}
  async function handleUrl(url: string) {
    const target = new URL(url)
    if (
      target.protocol !== 'app.dayloom.personal:' ||
      target.host !== 'auth' ||
      target.pathname !== '/callback'
    )
      return
    const ticket = target.searchParams.get('ticket')
    if (!ticket || processingTicket === ticket) return
    const { value: verifier } = await NativeBridge.getSecret({ key: 'login-verifier' })
    if (!verifier) return
    processingTicket = ticket
    try {
      const response = await fetch(`${baseUrl}/api/auth/exchange`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket, verifier }),
      })
      if (!response.ok) throw new Error('Native sign-in failed. Please sign in again.')
      await saveNativeSession((await response.json()) as Tokens)
      await NativeBridge.removeSecret({ key: 'login-verifier' })
      await Browser.close().catch(() => undefined)
      window.location.replace('/today')
    } catch (error) {
      window.dispatchEvent(
        new CustomEvent('dayloom-auth-error', {
          detail: error instanceof Error ? error.message : 'Sign-in failed.',
        }),
      )
    } finally {
      processingTicket = undefined
    }
  }
  const listener = await App.addListener('appUrlOpen', (event) => {
    void handleUrl(event.url)
  })
  const launch = await App.getLaunchUrl()
  if (launch?.url) await handleUrl(launch.url)
  return () => {
    void listener.remove()
  }
}

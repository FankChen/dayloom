import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  CircleCheck,
  Command,
  Inbox,
  Leaf,
  LoaderCircle,
  Menu,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sun,
  X,
} from 'lucide-react'
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api, ApiError, baseUrl, saveAccessToken } from './api'
import { setupNativeAuthentication, signIn } from './platform/native'
import { IconButton } from './components/ui'
import { LanguagePicker } from './components/LanguagePicker'
import { Activity as ActivityPage } from './pages/Activity'
import { Inbox as InboxPage } from './pages/Inbox'
import { Memories } from './pages/Memories'
import { SettingsPage } from './pages/Settings'
import { Tasks } from './pages/Tasks'
import { Today } from './pages/Today'
import { Guide } from './pages/Guide'
import { WorkspaceProvider } from './workspace'
import { useWorkspace } from './useWorkspace'

const queryClient = new QueryClient()
const navigation = [
  { path: '/today', label: 'Today', icon: Sun },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/tasks', label: 'Tasks', icon: CircleCheck },
  { path: '/memories', label: 'Memories', icon: Leaf },
  { path: '/activity', label: 'Activity', icon: Activity },
  { path: '/guide', label: 'Getting started', icon: BookOpen },
]

function ConnectionScreen() {
  const { t } = useTranslation()
  const { error, loading, refresh } = useWorkspace()
  const [token, setToken] = useState('')
  const [loginError, setLoginError] = useState('')
  useEffect(() => {
    const handler = (event: Event) => setLoginError((event as CustomEvent<string>).detail)
    window.addEventListener('dayloom-auth-error', handler)
    return () => window.removeEventListener('dayloom-auth-error', handler)
  }, [])
  const authentication = useQuery({
    queryKey: ['auth-config'],
    queryFn: () => api<{ mode: string; login_url: string }>('/api/auth/config'),
    retry: false,
  })
  const needsToken = error instanceof ApiError && error.status === 401
  if (loading)
    return (
      <div className="loading-screen">
        <LoaderCircle className="spin" size={24} />
        <span>{t('Opening your workspace...')}</span>
      </div>
    )
  return (
    <div className="connection-screen">
      <LanguagePicker />
      <ShieldCheck size={32} />
      <h1>{t(needsToken ? 'Your private workspace.' : 'Connection interrupted.')}</h1>
      <p>{t(error?.message ?? 'The server is not available.')}</p>
      {loginError && (
        <p role="alert" className="inline-error">
          {t(loginError)}
        </p>
      )}
      {needsToken && authentication.data?.mode === 'oidc' ? (
        <button
          className="button"
          onClick={() => {
            saveAccessToken('')
            void signIn(authentication.data!.login_url).catch((failure) =>
              setLoginError(failure instanceof Error ? failure.message : 'Sign-in unavailable.'),
            )
          }}
        >
          {t('Sign in to your account')} <ArrowUpRight size={16} />
        </button>
      ) : needsToken ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            saveAccessToken(token)
            refresh()
          }}
        >
          <label>
            {t('Workspace access token')}
            <input
              type="password"
              autoComplete="off"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              required
            />
          </label>
          <button className="button" type="submit">
            {t('Connect')} <ArrowUpRight size={16} />
          </button>
        </form>
      ) : (
        <button className="button" onClick={refresh}>
          <RefreshCw size={16} />
          {t('Reconnect')}
        </button>
      )}
    </div>
  )
}

function Shell() {
  const { t } = useTranslation()
  const { data, error, refresh, notice, clearNotice } = useWorkspace()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const pending = data?.actions.filter((action) => action.status === 'pending').length ?? 0
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        {t('Skip to content')}
      </a>
      <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`}>
        <NavLink to="/today" className="wordmark" onClick={() => setMobileOpen(false)}>
          <span className="brand-icon">
            <Command size={23} strokeWidth={1.6} />
          </span>
          dayloom<span className="brand-period">.</span>
        </NavLink>
        <div className="workspace-name">
          <span className="workspace-avatar">P</span>
          <div>
            <strong>
              {data?.account.mode === 'oidc' ? data.account.name : t('Personal workspace')}
            </strong>
            <span>{t('Just for you')}</span>
          </div>
        </div>
        <nav aria-label={t('Main navigation')}>
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <item.icon size={19} strokeWidth={1.7} />
              <span>{t(item.label)}</span>
              {item.path === '/activity' && pending > 0 && (
                <span className="nav-count">{pending}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="sidebar-caption">
            <span className="connection-dot online" />
            {t('Self-hosted workspace')}
          </span>
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileOpen(false)}
          >
            <Settings2 size={19} strokeWidth={1.7} />
            <span>{t('Settings')}</span>
          </NavLink>
          <div className="profile">
            <span className="profile-avatar">
              <Leaf size={17} />
            </span>
            <div>
              <strong>
                {t(data?.account.mode === 'oidc' ? 'Account connected' : 'Local workspace')}
              </strong>
              <span>Dayloom</span>
            </div>
            <ShieldCheck size={17} />
          </div>
        </div>
      </aside>
      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          aria-label={t('Close navigation')}
          onClick={() => setMobileOpen(false)}
        />
      )}
      <div className="workspace-main">
        <div className="topbar">
          <div className="breadcrumb">
            <IconButton
              className="menu-button"
              icon={Menu}
              label="Open navigation"
              onClick={() => setMobileOpen(true)}
            />
            <span>{t('Workspace')}</span>
            <span className="breadcrumb-slash">/</span>
            <strong>
              {t(navigation.find((item) => item.path === location.pathname)?.label ?? 'Settings')}
            </strong>
          </div>
          <div className="topbar-status">
            {data && (
              <span className={`mode-badge ${data.settings.provider.external ? 'live' : ''}`}>
                <span className="status-dot" />
                {!data.settings.provider.configured
                  ? t('Model not connected')
                  : data.settings.provider.external
                    ? data.settings.provider.model
                    : t('Offline demo')}
              </span>
            )}
            <IconButton icon={RefreshCw} label="Refresh workspace" onClick={refresh} />
          </div>
        </div>
        {error && data && (
          <div className="connection-warning" role="alert">
            {t('Connection interrupted. Showing last loaded data.')}
            <button onClick={refresh}>{t('Retry')}</button>
          </div>
        )}
        <main id="main">
          {data ? (
            <Routes>
              <Route path="/today" element={<Today />} />
              <Route path="/inbox" element={<InboxPage />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/memories" element={<Memories />} />
              <Route path="/activity" element={<ActivityPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/guide" element={<Guide key={data.account.workspace_id} />} />
              <Route path="*" element={<Navigate to="/today" replace />} />
            </Routes>
          ) : (
            <ConnectionScreen />
          )}
        </main>
        <footer className="page-footer">
          <span>{t('Make space for what matters.')}</span>
          <span>
            <ShieldCheck size={13} />
            {t('Your workspace. Your decisions.')}
          </span>
        </footer>
      </div>
      {notice && (
        <div
          className={`toast ${notice.error ? 'error' : ''}`}
          role={notice.error ? 'alert' : 'status'}
        >
          <span>{t(notice.text)}</span>
          <IconButton icon={X} label="Dismiss notification" onClick={clearNotice} />
        </div>
      )}
    </div>
  )
}

export default function App() {
  useEffect(() => {
    let cancelled = false
    let cleanup: (() => void) | undefined
    void setupNativeAuthentication(baseUrl)
      .then((remove) => {
        if (cancelled) remove()
        else cleanup = remove
      })
      .catch(() => {
        window.dispatchEvent(
          new CustomEvent('dayloom-auth-error', { detail: 'Native sign-in setup failed.' }),
        )
      })
    return () => {
      cancelled = true
      cleanup?.()
    }
  }, [])
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <WorkspaceProvider>
          <Shell />
        </WorkspaceProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

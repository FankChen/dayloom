import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  Activity,
  ArrowUpRight,
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
import { ApiError, saveAccessToken } from './api'
import { IconButton } from './components/ui'
import { Activity as ActivityPage } from './pages/Activity'
import { Inbox as InboxPage } from './pages/Inbox'
import { Memories } from './pages/Memories'
import { SettingsPage } from './pages/Settings'
import { Tasks } from './pages/Tasks'
import { Today } from './pages/Today'
import { WorkspaceProvider } from './workspace'
import { useWorkspace } from './useWorkspace'

const queryClient = new QueryClient()
const navigation = [
  { path: '/today', label: 'Today', icon: Sun },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/tasks', label: 'Tasks', icon: CircleCheck },
  { path: '/memories', label: 'Memories', icon: Leaf },
  { path: '/activity', label: 'Activity', icon: Activity },
]

function ConnectionScreen() {
  const { error, loading, refresh } = useWorkspace()
  const [token, setToken] = useState('')
  const needsToken = error instanceof ApiError && error.status === 401
  if (loading)
    return (
      <div className="loading-screen">
        <LoaderCircle className="spin" size={24} />
        <span>Opening your workspace...</span>
      </div>
    )
  return (
    <div className="connection-screen">
      <ShieldCheck size={32} />
      <h1>{needsToken ? 'Your private workspace.' : 'Connection interrupted.'}</h1>
      <p>{error?.message ?? 'The server is not available.'}</p>
      {needsToken ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            saveAccessToken(token)
            refresh()
          }}
        >
          <label>
            Workspace access token
            <input
              type="password"
              autoComplete="off"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              required
            />
          </label>
          <button className="button" type="submit">
            Connect <ArrowUpRight size={16} />
          </button>
        </form>
      ) : (
        <button className="button" onClick={refresh}>
          <RefreshCw size={16} />
          Reconnect
        </button>
      )}
    </div>
  )
}

function Shell() {
  const { data, error, refresh, notice, clearNotice } = useWorkspace()
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const pending = data?.actions.filter((action) => action.status === 'pending').length ?? 0
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
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
            <strong>Personal workspace</strong>
            <span>Just for you</span>
          </div>
        </div>
        <nav aria-label="Main navigation">
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              <item.icon size={19} strokeWidth={1.7} />
              <span>{item.label}</span>
              {item.path === '/activity' && pending > 0 && (
                <span className="nav-count">{pending}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="sidebar-caption">
            <span className="connection-dot online" />
            Self-hosted workspace
          </span>
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileOpen(false)}
          >
            <Settings2 size={19} strokeWidth={1.7} />
            <span>Settings</span>
          </NavLink>
          <div className="profile">
            <span className="profile-avatar">
              <Leaf size={17} />
            </span>
            <div>
              <strong>Your space</strong>
              <span>Dayloom / v0.1</span>
            </div>
            <ShieldCheck size={17} />
          </div>
        </div>
      </aside>
      {mobileOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
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
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{location.pathname.slice(1) || 'today'}</strong>
          </div>
          <div className="topbar-status">
            {data && (
              <span className={`mode-badge ${data.settings.provider.external ? 'live' : ''}`}>
                <span className="status-dot" />
                {data.settings.provider.external ? data.settings.provider.model : 'Offline demo'}
              </span>
            )}
            <IconButton icon={RefreshCw} label="Refresh workspace" onClick={refresh} />
          </div>
        </div>
        {error && data && (
          <div className="connection-warning" role="alert">
            Connection interrupted. Showing last loaded data.
            <button onClick={refresh}>Retry</button>
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
              <Route path="*" element={<Navigate to="/today" replace />} />
            </Routes>
          ) : (
            <ConnectionScreen />
          )}
        </main>
        <footer className="page-footer">
          <span>Make space for what matters.</span>
          <span>
            <ShieldCheck size={13} />
            Your workspace. Your decisions.
          </span>
        </footer>
      </div>
      {notice && (
        <div
          className={`toast ${notice.error ? 'error' : ''}`}
          role={notice.error ? 'alert' : 'status'}
        >
          <span>{notice.text}</span>
          <IconButton icon={X} label="Dismiss notification" onClick={clearNotice} />
        </div>
      )}
    </div>
  )
}

export default function App() {
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

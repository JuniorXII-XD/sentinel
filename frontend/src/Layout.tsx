import {
  Activity,
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronRight,
  FileText,
  FlaskConical,
  Layers,
  LayoutDashboard,
  LogOut,
  Menu,
  RefreshCw,
  Settings as SettingsIcon,
  Shield,
  ShieldAlert,
} from "lucide-react";
import { useContext, useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { api, setCsrf } from "./api";

import AlertDetail from "./pages/AlertDetail";
import Alerts from "./pages/Alerts";
import Analytics from "./pages/Analytics";
import Events from "./pages/Events";
import Overview from "./pages/Overview";
import Reports from "./pages/Reports";
import SettingsPage from "./pages/SettingsPage";
import { Auth, ErrorMessage, Workspace } from "./shared";
const navigation = [
  ["overview", "Overview", LayoutDashboard],
  ["events", "Security events", Activity],
  ["alerts", "Threat alerts", ShieldAlert],
  ["analytics", "Analytics", ChartNoAxesCombined],
  ["reports", "Reports", FileText],
  ["settings", "Settings", SettingsIcon],
] as const;
export default function Shell() {
  const auth = useContext(Auth);
  const location = useLocation();
  const [scope, setScope] = useState("live");
  const [days, setDays] = useState(7);
  const [revision, setRevision] = useState(0);
  const [menu, setMenu] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const page = navigation.find((x) => location.pathname.startsWith("/" + x[0]));
  useEffect(() => setMenu(false), [location.pathname]);
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setCsrf("");
      auth.setUser(null);
    } catch (e: any) {
      setLogoutError(e.message);
    }
  }
  if (!auth.user) return <Navigate to="/login" replace />;
  return (
    <Workspace.Provider value={{ scope, days, revision }}>
      <div className="app-shell">
        {menu && (
          <button
            className="scrim"
            aria-label="Close navigation"
            onClick={() => setMenu(false)}
          />
        )}
        <aside className={menu ? "sidebar show" : "sidebar"}>
          <NavLink to="/overview" className="brand">
            <Shield size={29} />
            <span>
              SENTINEL<span className="brand-mark">.</span>
            </span>
          </NavLink>
          <div className="workspace-label">
            <span className="workspace-icon">
              <Layers size={16} />
            </span>
            <div>
              Security workspace<small>Standard edition</small>
            </div>
            <ChevronRight size={14} />
          </div>
          <div className="nav-label">WORKSPACE</div>
          <nav>
            {navigation.map(([path, title, Icon]) => (
              <NavLink key={path} to={"/" + path}>
                <Icon size={18} />
                <span>{title}</span>
                {path === "alerts" && <span className="nav-dot" />}
              </NavLink>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="lab-card">
              <Shield size={21} />
              <strong>Signals, with context.</strong>
              <p>Alerts indicate patterns that need human investigation.</p>
              <NavLink to="/settings">
                View detection rules <ArrowUpRight size={14} />
              </NavLink>
            </div>
            <div className="profile">
              <span className="avatar">
                {auth.user.username.slice(0, 2).toUpperCase()}
              </span>
              <div>
                <strong>{auth.user.username}</strong>
                <small>{auth.user.role}</small>
              </div>
              <button
                className="icon-btn"
                title="Sign out"
                aria-label="Sign out"
                onClick={logout}
              >
                <LogOut size={17} />
              </button>
            </div>
          </div>
        </aside>
        <div className="workspace-main">
          <header className="topbar">
            <div className="breadcrumb">
              <button
                className="icon-btn mobile-menu"
                aria-label="Open navigation"
                onClick={() => setMenu(true)}
              >
                <Menu size={20} />
              </button>
              <span>Workspace</span>
              <ChevronRight size={13} />
              <strong>{page?.[1] || "Investigation"}</strong>
            </div>
            <div className="topbar-right">
              <span className="session-state">
                <span className="dot green" /> Session active
              </span>
              <span className="top-divider" />
              <span className="mono">STANDARD v1.0</span>
            </div>
          </header>
          <main>
            <ErrorMessage error={logoutError} />
            <div className="page-heading">
              <div>
                <span className="eyebrow">SECURITY OPERATIONS</span>
                <h1>{page?.[1] || "Alert investigation"}</h1>
                <p>
                  {
                    (
                      {
                        overview: "Your security posture, at a glance.",
                        events: "A searchable trail of security activity.",
                        alerts: "Investigate signals. Document the outcome.",
                        analytics:
                          "Understand patterns across your environment.",
                        reports:
                          "Turn security activity into actionable insight.",
                        settings:
                          "Manage access and understand your detection coverage.",
                      } as Record<string, string>
                    )[page?.[0] || "alerts"]
                  }
                </p>
              </div>
              <div className="toolbar">
                <select
                  aria-label="Data source"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                >
                  <option value="live">Live events</option>
                  {auth.demo && <option value="demo">Demo dataset</option>}
                </select>
                <select
                  aria-label="Time range"
                  value={days}
                  onChange={(e) => setDays(+e.target.value)}
                >
                  <option value={1}>Last 24 hours</option>
                  <option value={7}>Last 7 days</option>
                  <option value={30}>Last 30 days</option>
                  <option value={90}>Last 90 days</option>
                </select>
                <button
                  className="icon-btn bordered"
                  aria-label="Refresh data"
                  onClick={() => setRevision((x) => x + 1)}
                >
                  <RefreshCw size={16} />
                </button>
              </div>
            </div>
            {scope === "demo" && (
              <div className="demo-banner">
                <FlaskConical size={16} />
                <span>
                  <b>DEMO DATASET</b> Synthetic events for an authorized local
                  lab. No real attacks or external scans.
                </span>
              </div>
            )}
            <Routes>
              <Route path="overview" element={<Overview />} />
              <Route path="events" element={<Events />} />
              <Route path="alerts" element={<Alerts />} />
              <Route path="alerts/:id" element={<AlertDetail />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="reports" element={<Reports />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/overview" replace />} />
            </Routes>
            <footer className="page-footer">
              <span>
                <Shield size={13} /> SENTINEL · Security event intelligence
              </span>
              <span>Times shown in your timezone · Charts in UTC</span>
            </footer>
          </main>
        </div>
      </div>
    </Workspace.Provider>
  );
}

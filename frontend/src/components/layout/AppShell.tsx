import { NavLink, Outlet } from "react-router-dom";
import "./AppShell.css";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "◧" },
  { to: "/scenarios", label: "Sample scenarios", icon: "✦" },
  { to: "/experiments/new", label: "New experiment", icon: "+" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-brand">
          <span className="app-brand-mark">SP</span>
          <div>
            <div className="app-brand-name">Synthetic Users</div>
            <div className="app-brand-sub">Research workspace</div>
          </div>
        </div>
        <nav className="app-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `app-nav-link${isActive ? " app-nav-link-active" : ""}`}
            >
              <span className="app-nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="app-sidebar-footer">
          <div className="app-sidebar-footer-badge">Qwen3-8B · Hugging Face</div>
        </div>
      </aside>
      <main className="app-content">
        <div className="app-content-inner">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

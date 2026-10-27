import { GraduationCap, LogOut } from "lucide-react";
import type { User } from "../../types/api";
import type { RoutePath } from "../../types/routes";
import { NAV_SECTIONS, NAVIGATION_ITEMS } from "../../routes/navigation";
import { Badge } from "../ui/Badge";

interface SidebarProps {
  readonly user: User;
  readonly activeRoute: RoutePath | string;
  readonly aiIsMock: boolean;
  readonly unread?: number;
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly onLogout: () => void;
}

export function Sidebar({
  user,
  activeRoute,
  aiIsMock,
  unread = 0,
  isOpen,
  onClose,
  onLogout,
}: SidebarProps) {
  const current = activeRoute === "result" ? "results" : activeRoute === "module" ? "learn" : activeRoute;

  const visible = NAVIGATION_ITEMS.filter((item) => item.category !== "admin" || user.is_admin);

  return (
    <aside
      className={`sidebar ${isOpen ? "open" : ""}`}
      aria-label="Application navigation"
    >
      <div className="sidebar-header">
        <a href="#/dashboard" className="brand brand-lg" onClick={onClose}>
          <GraduationCap size={24} aria-hidden /> Pragya<span className="brand-x">X</span>
        </a>
        <p className="tagline">AI-Powered Practical Learning</p>
      </div>

      <nav aria-label="Main Navigation" style={{ display: "flex", flexDirection: "column" }}>
        {NAV_SECTIONS.map((section) => {
          const items = visible.filter((i) => i.category === section.key);
          if (!items.length) return null;
          return (
            <div key={section.key} className="nav-group">
              <span className="nav-section-title">{section.title}</span>
              {items.map(({ path, label, icon: Icon }) => (
                <a
                  key={path}
                  href={`#/${path}`}
                  className={`nav-link ${current === path ? "active" : ""}`}
                  aria-current={current === path ? "page" : undefined}
                  onClick={onClose}
                >
                  <Icon size={18} aria-hidden />
                  <span>{label}</span>
                  {path === "notifications" && unread > 0 && (
                    <span className="nav-count" aria-label={`${unread} unread`}>{unread}</span>
                  )}
                </a>
              ))}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-foot">
        {aiIsMock && (
          <Badge
            variant="demo"
            title="Responses are generated from an offline deterministic provider."
          >
            Demo AI Mode
          </Badge>
        )}

        <div className="me">
          <div className="avatar" aria-hidden>
            {user.name.charAt(0).toUpperCase()}
          </div>
          <div className="me-text">
            <strong>{user.name}</strong>
            <small>{user.email}</small>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-ghost btn-sm btn-block"
          onClick={onLogout}
          aria-label="Log out of PragyaX"
        >
          <LogOut size={15} aria-hidden />
          <span>Log out</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;

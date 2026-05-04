import React from "react";
import { Moon, Sun, Compass, LayoutDashboard, PanelLeftClose, Plus } from "lucide-react";
import QueryHistory from "./QueryHistory";
import "./Sidebar.css";

const Sidebar = ({
  queryHistory,
  isDark,
  toggleTheme,
  isOpen,
  toggleSidebar,
  onLoadHistory,
  onNewQuery,
}) => {
  return (
    <aside className={`sidebar-container ${isOpen ? "open" : "closed"}`} aria-label="Sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo" aria-label="BIS Compass">
          <span className="sidebar-logo-mark" aria-hidden="true">
            <Compass size={18} />
          </span>
          <div className="sidebar-logo-text">
            <h2 className="sidebar-title">BIS Compass</h2>
            <div className="sidebar-subtitle">Standards discovery</div>
          </div>
        </div>

        <button
          type="button"
          className="sidebar-close-btn"
          onClick={toggleSidebar}
          aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
          title={isOpen ? "Close sidebar" : "Open sidebar"}
        >
          <PanelLeftClose size={20} />
        </button>
      </div>

      <div className="sidebar-content">
        <div className="new-query-container">
          <button type="button" className="new-query-btn" onClick={onNewQuery}>
            <Plus size={18} />
            <span>New query</span>
          </button>
        </div>

        <div className="sidebar-section-title" aria-label="Workspace">
          <LayoutDashboard size={14} />
          <span>Workspace</span>
        </div>

        <QueryHistory queryHistory={queryHistory} onLoadHistory={onLoadHistory} />
      </div>

      <div className="sidebar-footer">
        <button type="button" className="sidebar-theme-toggle" onClick={toggleTheme}>
          {isDark ? (
            <>
              <Sun size={18} />
              <span>Light mode</span>
            </>
          ) : (
            <>
              <Moon size={18} />
              <span>Dark mode</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
import React from "react";
import { Compass, Activity, Database, GitMerge, PanelLeftOpen } from "lucide-react";
import "./Header.css";

const Header = ({ isDark, toggleSidebar, isSidebarOpen }) => {
  return (
    <header className="header glass" role="banner">
      <div className="header__inner">
        <div className="header-left">
          {!isSidebarOpen && (
            <button
              type="button"
              className="sidebar-toggle-btn"
              onClick={toggleSidebar}
              aria-label="Open sidebar"
            >
              <PanelLeftOpen size={20} />
            </button>
          )}

          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              <Compass size={20} />
            </span>

            <div className="brand__text">
              <h1 className="brand__title">BIS Compass</h1>
              <span className="brand__tagline">Compliance Intelligence Platform</span>
            </div>
          </div>
        </div>

        <div className="header-right">
          <div className="metrics-badges" role="list" aria-label="System metrics">
            <div className="badge" role="listitem" title="Indexed standards">
              <Database size={14} />
              <span className="mono">Standards: 156</span>
            </div>

            <div className="badge" role="listitem" title="Average response latency">
              <Activity size={14} />
              <span className="mono">Latency: 0.9s</span>
            </div>

            <div className="badge" role="listitem" title="Pipeline stages">
              <GitMerge size={14} />
              <span className="mono">Pipeline: 9</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
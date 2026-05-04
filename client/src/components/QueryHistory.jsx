import React, { useCallback, useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, History } from "lucide-react";
import "./QueryHistory.css";

const normalizeStdId = (id) => String(id || "").replace(" : ", ":");

const buildPreview = (standards) => {
  const list = Array.isArray(standards) ? standards : [];
  const ids = list.map((s) => normalizeStdId(s?.id)).filter(Boolean);
  const shown = ids.slice(0, 2);
  const more = Math.max(0, ids.length - shown.length);
  if (!shown.length) return null;
  return `${shown.join(" · ")}${more ? `  +${more}` : ""}`;
};

const QueryHistory = ({ queryHistory = [], onLoadHistory }) => {
  const reduceMotion = useReducedMotion();
  const [expandedId, setExpandedId] = useState(null);

  const items = useMemo(() => (Array.isArray(queryHistory) ? queryHistory : []), [queryHistory]);

  const toggleExpanded = useCallback((id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  if (items.length === 0) {
    return (
      <div className="query-history-container glass-panel qh-empty" aria-label="Query history">
        <div className="qh-emptyIcon" aria-hidden="true">
          <History size={18} />
        </div>
        <div className="qh-emptyText">
          <div className="qh-emptyTitle">No recent queries</div>
          <div className="qh-emptySub">Your history will appear here as you search.</div>
        </div>
      </div>
    );
  }

  return (
    <section className="query-history-container glass-panel" aria-label="Recent queries">
      <div className="qh-header">
        <div className="qh-headerLeft">
          <History className="qh-icon" size={18} />
          <h3 className="panel-title">Recent</h3>
        </div>
        <div className="qh-count mono" title="Saved queries">
          {items.length}
        </div>
      </div>

      <ul className="qh-list" role="list">
        {items.map((item) => {
          const isExpanded = expandedId === item.id;
          const standards = Array.isArray(item.standards) ? item.standards : [];
          const top3 = standards.slice(0, 3);
          const preview = buildPreview(standards);

          return (
            <li key={item.id} className={`qh-item ${isExpanded ? "isExpanded" : ""}`} role="listitem">
              <div className="qh-row">
                {/* Summary (click toggles expand) */}
                <button
                  type="button"
                  className="qh-summary"
                  onClick={() => toggleExpanded(item.id)}
                  aria-expanded={isExpanded}
                  aria-controls={`qh-expand-${item.id}`}
                  title={item.query}
                >
                  <div className="qh-time mono">{item.timestamp || "—"}</div>
                  <div className="qh-query">{item.query || "Untitled query"}</div>
                  {preview && <div className="qh-preview mono">{preview}</div>}
                </button>

                {/* Actions (separate buttons; no nesting) */}
                <div className="qh-actions" role="group" aria-label="History actions">
                  <button
                    type="button"
                    className="qh-loadBtn"
                    onClick={() => onLoadHistory?.(item)}
                    title="Load this query"
                  >
                    Load
                  </button>

                  <button
                    type="button"
                    className="qh-expandBtn"
                    onClick={() => toggleExpanded(item.id)}
                    aria-label={isExpanded ? "Collapse" : "Expand"}
                    title={isExpanded ? "Collapse" : "Expand"}
                  >
                    <motion.span
                      initial={false}
                      animate={{ rotate: isExpanded ? 180 : 0 }}
                      transition={{ duration: reduceMotion ? 0 : 0.18 }}
                      className="qh-chevIcon"
                    >
                      <ChevronDown size={18} />
                    </motion.span>
                  </button>
                </div>
              </div>

              <AnimatePresence initial={false}>
                {isExpanded && (
                  <motion.div
                    id={`qh-expand-${item.id}`}
                    className="qh-expand"
                    initial={reduceMotion ? { opacity: 1 } : { height: 0, opacity: 0 }}
                    animate={reduceMotion ? { opacity: 1 } : { height: "auto", opacity: 1 }}
                    exit={reduceMotion ? { opacity: 0 } : { height: 0, opacity: 0 }}
                    transition={{ duration: reduceMotion ? 0 : 0.2, ease: "easeInOut" }}
                  >
                    <div className="qh-expandInner">
                      <div className="qh-metaLabel">Top matched standards</div>
                      <div className="qh-tags">
                        {top3.length ? (
                          top3.map((std) => (
                            <span key={std.id} className="qh-tag mono">
                              {normalizeStdId(std.id)}
                            </span>
                          ))
                        ) : (
                          <span className="qh-none">No standards found</span>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </li>
          );
        })}
      </ul>
    </section>
  );
};

export default QueryHistory;
import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Zap, Tag, Timer, BarChart2 } from "lucide-react";
import "./QueryDetails.css";

const STOPWORDS = new Set([
  "the","and","for","with","from","this","that","into","your","you","are","was","were",
  "have","has","had","will","shall","should","would","can","could","may","might",
]);

function uniqueExpandedTerms(expandedQuery = "") {
  const raw = String(expandedQuery)
    .replace(/[^\w\s:-]/g, " ")
    .split(/\s+/)
    .map((s) => s.trim())
    .filter(Boolean);

  const out = [];
  const seen = new Set();

  for (const t of raw) {
    const norm = t.toLowerCase();
    if (norm.length <= 2) continue;
    if (STOPWORDS.has(norm)) continue;
    if (seen.has(norm)) continue;
    seen.add(norm);
    out.push(t);
  }
  return out;
}

const fmtCategory = (c) => (c ? String(c).replaceAll("_", " ") : "—");

const QueryDetails = ({ meta }) => {
  const [showAllTerms, setShowAllTerms] = useState(false);

  const terms = useMemo(
    () => uniqueExpandedTerms(meta?.expanded_query ?? ""),
    [meta?.expanded_query]
  );

  const MAX_TERMS = 8; // keep clean
  const shown = showAllTerms ? terms : terms.slice(0, MAX_TERMS);
  const more = Math.max(0, terms.length - shown.length);

  if (!meta) return null;

  return (
    <motion.section
      className="query-details-container glass-panel qd2"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      aria-label="Query intelligence"
    >
      {/* Header */}
      <header className="qd2__head">
        <div className="qd2__title">
          <span className="qd2__mark" aria-hidden="true">
            <Zap size={16} />
          </span>
          <div className="qd2__titleText">
            <div className="qd2__h">Query Intelligence</div>
            <div className="qd2__sub">Compact overview</div>
          </div>
        </div>

        <div className="qd2__right">
          <span className="qd2__pill" title="Latency">
            <Timer size={14} />
            <span className="mono">{meta.latency_seconds ?? "—"}s</span>
          </span>
        </div>
      </header>

      {/* Body (field layout = aligned + not messy) */}
      <div className="qd2__body">
        <div className="qd2__fields" role="list" aria-label="Query details">
          <div className="qd2__field" role="listitem">
            <div className="qd2__key">Input</div>
            <div className="qd2__val qd2__val--clamp" title={meta.original_query || ""}>
              {meta.original_query ? `“${meta.original_query}”` : "—"}
            </div>
          </div>

          <div className="qd2__field" role="listitem">
            <div className="qd2__key">Category</div>
            <div className="qd2__val">
              <span className="qd2__catPill" title="Detected category">
                <Tag size={14} />
                {fmtCategory(meta.detected_category)}
              </span>
            </div>
          </div>

          <div className="qd2__field" role="listitem">
            <div className="qd2__key">Expanded</div>
            <div className="qd2__val">
              <div className="qd2__chips" aria-label="Expanded terms">
                {shown.length ? (
                  <>
                    {shown.map((t, i) => (
                      <span key={`${t}-${i}`} className="qd2__chip">
                        {t}
                      </span>
                    ))}

                    {more > 0 && !showAllTerms && (
                      <button
                        type="button"
                        className="qd2__chip qd2__chipBtn"
                        onClick={() => setShowAllTerms(true)}
                        title="Show all terms"
                      >
                        +{more}
                      </button>
                    )}

                    {showAllTerms && terms.length > MAX_TERMS && (
                      <button
                        type="button"
                        className="qd2__chip qd2__chipBtn"
                        onClick={() => setShowAllTerms(false)}
                        title="Show fewer terms"
                      >
                        Less
                      </button>
                    )}
                  </>
                ) : (
                  <span className="qd2__muted">—</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="qd2__statsCard" aria-label="Pipeline stats">
          <div className="qd2__statsHead">
            <BarChart2 size={14} />
            <span>Pipeline stats</span>
          </div>

          <div className="qd2__stats">
            <div className="qd2__stat">
              <div className="qd2__statNum mono">{meta.candidates_retrieved ?? "—"}</div>
              <div className="qd2__statLbl">Retrieved</div>
            </div>
            <div className="qd2__stat">
              <div className="qd2__statNum mono">{meta.candidates_reranked ?? "—"}</div>
              <div className="qd2__statLbl">Reranked</div>
            </div>
            <div className="qd2__stat qd2__stat--accent">
              <div className="qd2__statNum mono">{meta.candidates_output ?? "—"}</div>
              <div className="qd2__statLbl">Output</div>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  );
};

export default QueryDetails;
import React, { useMemo, useState, useId } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, ChevronUp, ShieldCheck, Star } from "lucide-react";
import "./ResultCard.css";

const clamp01 = (n) => Math.max(0, Math.min(1, Number(n) || 0));
const formatPct = (conf) => `${(clamp01(conf) * 100).toFixed(0)}%`;

const toneFromRank = (rank) => {
  if (rank === 1) return "high";
  if (rank <= 3) return "medium";
  return "low";
};

const getFirstSentence = (text = "") => {
  const t = String(text).trim();
  if (!t) return "";
  const idx = t.search(/[.!?]\s/);
  if (idx === -1) return t;
  return t.slice(0, idx + 1);
};

const takeWithMore = (arr, limit) => {
  const a = Array.isArray(arr) ? arr : [];
  const shown = a.slice(0, limit);
  return { shown, more: Math.max(0, a.length - shown.length) };
};

const ResultCard = ({ result, index = 0 }) => {
  const reduceMotion = useReducedMotion();
  const detailsId = useId();

  const rank = Number(result?.rank) || 0;
  const isTop = rank === 1;
  const tone = useMemo(() => toneFromRank(rank), [rank]);

  const conf = clamp01(result?.confidence);

  const matched = Array.isArray(result?.matched_keywords) ? result.matched_keywords : [];
  const related = Array.isArray(result?.related_standards) ? result.related_standards : [];

  const { shown: kwShown, more: kwMore } = useMemo(() => takeWithMore(matched, 4), [matched]);
  const { shown: relShown, more: relMore } = useMemo(() => takeWithMore(related, 4), [related]);

  const rationale = String(result?.rationale || "").trim();
  const rationaleSummary = useMemo(() => {
    const s = getFirstSentence(rationale);
    return s || rationale;
  }, [rationale]);

  // Expand top result only by default (keeps UI calm)
  const [expanded, setExpanded] = useState(isTop);

  return (
    <motion.article
      className="rc"
      data-tone={tone}
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={reduceMotion ? {} : { opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: Math.min(index * 0.04, 0.18) }}
    >
      <div className="rc__row">
        <div className="rc__main">
          <div className="rc__topline">
            <span className={`rc__rank ${isTop ? "isTop" : ""}`}>#{rank}</span>
            <span className="rc__id mono">{result?.id || "—"}</span>

            {isTop && (
              <span className="rc__best">
                <Star size={14} />
                Best match
              </span>
            )}
          </div>

          <h3 className="rc__title" title={result?.title}>
            {result?.title || "Untitled standard"}
          </h3>

          {/* One line only (clamped) */}
          <p className="rc__why" title={rationale}>
            {rationaleSummary || "—"}
          </p>

          {/* Small signal chips, capped */}
          <div className="rc__signals" aria-label="Matched signals">
            {result?.category ? (
              <span className="rc__chip rc__chip--cat">
                {String(result.category).replaceAll("_", " ")}
              </span>
            ) : null}

            {kwShown.map((kw, i) => (
              <span key={`${kw}-${i}`} className="rc__chip">
                {kw}
              </span>
            ))}

            {kwMore > 0 && <span className="rc__chip rc__chip--more">+{kwMore}</span>}
          </div>
        </div>

        <div className="rc__side">
          <div className="rc__confidence" title="Model confidence">
            <ShieldCheck size={14} />
            <span className="rc__confText">
              <span className="mono">{formatPct(conf)}</span>
            </span>
          </div>

          <button
            type="button"
            className="rc__toggle"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            aria-controls={detailsId}
            title={expanded ? "Hide details" : "View details"}
          >
            {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>
        </div>
      </div>

      {/* Subtle confidence bar (no extra text) */}
      <div className="rc__bar" aria-hidden="true">
        <motion.div
          className="rc__barFill"
          initial={reduceMotion ? false : { width: 0 }}
          animate={{ width: `${conf * 100}%` }}
          transition={{ duration: reduceMotion ? 0 : 0.45, delay: 0.05 }}
        />
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            id={detailsId}
            className="rc__details"
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0, height: 0 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, height: "auto" }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
          >
            <div className="rc__detailGrid">
              <div className="rc__detailBlock">
                <div className="rc__detailLabel">Rationale</div>
                <div className="rc__detailText">{rationale || "—"}</div>
              </div>

              <div className="rc__detailBlock">
                <div className="rc__detailLabel">Related standards</div>
                <div className="rc__tagRow">
                  {relShown.length ? (
                    <>
                      {relShown.map((rs) => (
                        <span key={rs} className="rc__tag mono">
                          {rs}
                        </span>
                      ))}
                      {relMore > 0 && <span className="rc__tag rc__tag--more">+{relMore}</span>}
                    </>
                  ) : (
                    <span className="rc__muted">—</span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
};

export default ResultCard;
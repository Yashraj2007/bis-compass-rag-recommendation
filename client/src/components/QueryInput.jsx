import React, { useEffect, useMemo, useRef } from "react";
import { Search, Tag } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import "./QueryInput.css";

const EXAMPLE_CHIPS = [
  "33 Grade OPC Cement",
  "Coarse & Fine Aggregates",
  "Precast Concrete Pipes",
  "Asbestos Cement Sheets",
  "Portland Slag Cement",
  "Masonry Cement",
];

const QueryInput = ({ query, setQuery, onSearch, isSearching, detectedCategory, onTyping }) => {
  const textareaRef = useRef(null);

  const canSearch = useMemo(() => !!query?.trim() && !isSearching, [query, isSearching]);

  // Autosize textarea (keeps your behavior but more stable)
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;

    el.style.height = "0px";
    const next = Math.min(el.scrollHeight, 240);
    el.style.height = `${next}px`;
  }, [query]);

  const submit = () => {
    const q = (query || "").trim();
    if (!q || isSearching) return;
    onSearch?.(q);
  };

  const handleChipClick = (chipText) => {
    if (isSearching) return;
    setQuery(chipText);
    onSearch?.(chipText);
  };

  return (
    <div className="query-input-container">
      <div className="input-wrapper glass-panel">
        <div className="input-topRow">
          <textarea
            ref={textareaRef}
            className="query-textarea"
            rows={1}
            placeholder="Describe your product to find applicable BIS standards… e.g., We manufacture 33 Grade Ordinary Portland Cement"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              onTyping?.();
            }}
            onFocus={() => onTyping?.()}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            aria-label="Product description"
          />
        </div>

        <div className="input-footer">
          <div className="input-footerLeft">
            <AnimatePresence initial={false}>
              {detectedCategory ? (
                <motion.div
                  key="cat"
                  className="category-tag"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  transition={{ duration: 0.18 }}
                  title="Detected category"
                >
                  <Tag size={14} />
                  <span className="category-text">
                    {String(detectedCategory).replaceAll("_", " ")}
                  </span>
                </motion.div>
              ) : (
                <div className="helperHint" key="hint">
                  Press <span className="kbd">Enter</span> to search · <span className="kbd">Shift</span>+
                  <span className="kbd">Enter</span> for newline
                </div>
              )}
            </AnimatePresence>
          </div>

          <button
            type="button"
            className="btn-primary search-btn"
            onClick={submit}
            disabled={!canSearch}
            aria-busy={isSearching}
          >
            <span className="search-btnText">{isSearching ? "Processing…" : "Find standards"}</span>
            <Search size={18} className={isSearching ? "spin" : ""} />
          </button>
        </div>
      </div>

      <div className="example-chips" aria-label="Examples">
        {EXAMPLE_CHIPS.map((chip) => (
          <button
            key={chip}
            type="button"
            className="chip"
            onClick={() => handleChipClick(chip)}
            disabled={isSearching}
            title="Use this example"
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
};

export default QueryInput;
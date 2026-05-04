import React, { useMemo } from "react";
import { motion } from "framer-motion";
import {
  Check,
  Settings,
  Expand,
  Tag,
  Search,
  TrendingUp,
  Layers,
  Filter,
  Zap,
  FileOutput,
} from "lucide-react";
import "./PipelineViz.css";

const STAGES = [
  { id: "normalize", label: "Normalize", icon: Settings, tooltip: "Cleaned: '33 grade opc cement'" },
  { id: "expand", label: "Expand", icon: Expand, tooltip: "Added: ordinary portland cement, IS 269" },
  { id: "categorize", label: "Categorize", icon: Tag, tooltip: "Category: cement_opc" },
  { id: "retrieve", label: "Retrieve", icon: Search, tooltip: "Found 20 candidates (FAISS + BM25 RRF)" },
  { id: "meta_boost", label: "Meta Boost", icon: TrendingUp, tooltip: "Boosted category-matching docs" },
  { id: "cross_encode", label: "Cross-Encode", icon: Layers, tooltip: "Reranked top 10 with ms-marco-MiniLM" },
  { id: "rule_boost", label: "Rule Boost", icon: Zap, tooltip: "Applied domain anchor matching" },
  { id: "deduplicate", label: "Deduplicate", icon: Filter, tooltip: "5 unique standards" },
  { id: "output", label: "Output", icon: FileOutput, tooltip: "Done in 0.87s" },
];

const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

const PipelineViz = ({ activeStageIndex = 0 }) => {
  const active = useMemo(
    () => clamp(Number(activeStageIndex) || 0, 0, STAGES.length - 1),
    [activeStageIndex]
  );

  return (
    <section className="pipeline-container glass-panel" aria-label="RAG pipeline execution">
      <div className="pipeline-head">
        <h3 className="pipeline-title">RAG Pipeline Execution</h3>
        <div className="pipeline-subtitle">
          Stage <span className="mono">{active + 1}</span> of{" "}
          <span className="mono">{STAGES.length}</span>
        </div>
      </div>

      <div className="pipeline-track" role="list" aria-label="Pipeline stages">
        {STAGES.map((stage, idx) => {
          const isLast = idx === STAGES.length - 1;
          const isDone = idx < active || (active === STAGES.length - 1 && idx === active);
          const isActive = idx === active;

          const status = isDone ? "done" : isActive ? "active" : "todo";
          const Icon = stage.icon;

          const tooltipId = `pipeline-tip-${stage.id}`;

          return (
            <React.Fragment key={stage.id}>
              <div
                className={`stage ${status} ${isActive ? "show-tooltip" : ""}`}
                role="listitem"
              >
                <button
                  type="button"
                  className="node-wrapper"
                  aria-current={isActive ? "step" : undefined}
                  aria-describedby={tooltipId}
                >
                  <motion.div
                    className={`pipeline-node ${status} ${isLast && isDone ? "complete" : ""}`}
                    initial={false}
                    animate={{ scale: isActive ? 1 : 0.96, opacity: isDone || isActive ? 1 : 0.55 }}
                    transition={{ duration: 0.2 }}
                  >
                    {isDone && !isLast ? <Check size={16} /> : <Icon size={16} />}
                  </motion.div>

                  <span className={`node-label ${status}`}>{stage.label}</span>
                </button>

                <div id={tooltipId} className="node-tooltip" role="tooltip">
                  {stage.tooltip}
                </div>
              </div>

              {!isLast && (
                <div className="connector" aria-hidden="true">
                  <motion.div
                    className="connector-fill"
                    initial={false}
                    animate={{ width: idx < active ? "100%" : "0%" }}
                    transition={{ duration: 0.22, ease: "linear" }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
};

export default PipelineViz;
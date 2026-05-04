import React, { useCallback, useMemo, useState } from "react";
import { Download } from "lucide-react";
import "./ExportButton.css";

function safeFilePart(s) {
  return String(s || "")
    .trim()
    .slice(0, 48)
    .replaceAll(/[^a-zA-Z0-9-_ ]/g, "")
    .replaceAll(/\s+/g, "_");
}

function downloadJson(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}

const ExportButton = ({ results = [], query = "", meta = null }) => {
  const [isExporting, setIsExporting] = useState(false);

  const canExport = useMemo(
    () => Array.isArray(results) && results.length > 0 && !isExporting,
    [results, isExporting]
  );

  const handleExport = useCallback(() => {
    if (!Array.isArray(results) || results.length === 0 || isExporting) return;

    setIsExporting(true);

    const payload = {
      generated_on: new Date().toISOString(),
      query,
      meta: meta ?? undefined,
      results,
    };

    const name = safeFilePart(query) || "BIS_Export";
    const filename = `BIS_${name}_${Date.now()}.json`;

    try {
      downloadJson(payload, filename);
    } finally {
      // small delay so the UI state feels intentional
      window.setTimeout(() => setIsExporting(false), 250);
    }
  }, [results, query, meta, isExporting]);

  return (
    <div className="exportButtonWrap">
      <button
        type="button"
        className="exportButton"
        onClick={handleExport}
        disabled={!canExport}
        aria-busy={isExporting}
        title={canExport ? "Download JSON export" : "Run a search to enable export"}
      >
        <span className={`exportIcon ${isExporting ? "isLoading" : ""}`} aria-hidden="true">
          <Download size={18} />
        </span>

        <span className="exportText">
          <span className="exportTitle">
            {isExporting ? "Preparing export…" : "Download results export"}
          </span>
          <span className="exportSubtitle">JSON snapshot (results + metadata)</span>
        </span>

        <span className="exportRight">
          <span className="exportCta">{isExporting ? "…" : "JSON"}</span>
        </span>
      </button>
    </div>
  );
};

export default ExportButton;
import React from 'react';
import QueryDetails from './QueryDetails';
import ExportButton from './ExportButton';

const SidePanel = ({ results, meta, originalQuery }) => {
  return (
    <div className="side-panel-container" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      <QueryDetails meta={meta} />
      {results && results.length > 0 && (
        <ExportButton results={results} query={originalQuery} />
      )}
    </div>
  );
};

export default SidePanel;

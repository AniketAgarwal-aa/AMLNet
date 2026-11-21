import React from 'react';
import { useResearch } from '../context/ResearchContext';

export function DatasetSelector({ compact = false }) {
  const { selectedTier, setSelectedTier, resetToDefault, DEFAULT_TIER, VALID_TIERS } = useResearch();

  const tierSubtitles = {
    '100': '100 accts / 17K tx',
    '1K': '1K accts / 117K tx (Full)',
    '10K': '10K accts / 1.3M tx',
    '100K': '100K accts / 12.5M tx ★ DEFAULT',
    '1M': '1M accts / 125M tx (Stream)'
  };

  if (compact) {
    return (
      <div className="dataset-selector-compact">
        <span className="selector-label">Dataset:</span>
        <div className="tier-pills">
          {VALID_TIERS.map((tier) => (
            <button
              key={tier}
              type="button"
              className={`tier-pill ${selectedTier === tier ? 'active' : ''} ${tier === DEFAULT_TIER ? 'default-pill' : ''}`}
              onClick={() => setSelectedTier(tier)}
              title={tierSubtitles[tier]}
            >
              {tier}
              {tier === DEFAULT_TIER && <span className="star-tag">★</span>}
            </button>
          ))}
          {selectedTier !== DEFAULT_TIER && (
            <button
              type="button"
              className="reset-pill"
              onClick={resetToDefault}
              title="Reset selection back to default 100K flagship dataset"
            >
              ↺ Reset to 100K
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="dataset-selector-card">
      <div className="selector-header">
        <div className="selector-title-group">
          <div>
            <h3 className="selector-heading">AMLSim Benchmark Dataset</h3>
            <p className="selector-subheading">
              Select any of the 5 verified IBM AMLSim benchmark scale tiers to explore models, topology, and metrics.
            </p>
          </div>
        </div>
        <div className="selector-actions">
          {selectedTier !== DEFAULT_TIER ? (
            <button
              type="button"
              className="secondary reset-btn"
              onClick={resetToDefault}
            >
              ↺ Reset to 100K (Default)
            </button>
          ) : (
            <span className="default-indicator-badge">
              ✓ 100K Flagship Tier Active
            </span>
          )}
        </div>
      </div>

      <div className="tier-grid">
        {VALID_TIERS.map((tier) => {
          const isSelected = selectedTier === tier;
          const isDefault = tier === DEFAULT_TIER;
          return (
            <button
              key={tier}
              type="button"
              className={`tier-card-btn ${isSelected ? 'selected' : ''} ${isDefault ? 'is-default' : ''}`}
              onClick={() => setSelectedTier(tier)}
            >
              <div className="tier-card-top">
                <span className="tier-name">{tier}</span>
                {isDefault && <span className="default-badge">DEFAULT</span>}
              </div>
              <div className="tier-subtext">{tierSubtitles[tier]}</div>
              <div className="tier-select-indicator">
                {isSelected ? '● Currently Active' : 'Select Tier'}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

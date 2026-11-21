import React, { createContext, useContext, useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../api';

const DEFAULT_TIER = '100K';
const VALID_TIERS = ['100', '1K', '10K', '100K', '1M'];
const STORAGE_KEY = 'amlnet_selected_tier';

const ResearchContext = createContext(null);

export function useResearch() {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error('useResearch must be used within a ResearchProvider');
  }
  return context;
}

export function ResearchProvider({ children }) {
  // Read initial tier from URL query param (?tier=100K) or localStorage, defaulting strictly to 100K
  const getInitialTier = () => {
    try {
      const params = new URLSearchParams(window.location.search);
      const urlTier = params.get('tier');
      if (urlTier && VALID_TIERS.includes(urlTier.toUpperCase())) {
        return urlTier.toUpperCase();
      }
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && VALID_TIERS.includes(stored.toUpperCase())) {
        return stored.toUpperCase();
      }
    } catch {
      // Fallback
    }
    return DEFAULT_TIER;
  };

  const [selectedTier, setSelectedTierState] = useState(getInitialTier);
  const [rankingMetric, setRankingMetric] = useState('f1');
  const [datasetsData, setDatasetsData] = useState(null);
  const [tierExperiments, setTierExperiments] = useState([]);
  const [allExperiments, setAllExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Stale-response protection counter
  const fetchCounterRef = useRef(0);

  // Sync selection to localStorage and URL query param
  const setSelectedTier = (tier) => {
    const sanitized = VALID_TIERS.includes(tier) ? tier : DEFAULT_TIER;
    setSelectedTierState(sanitized);
    try {
      localStorage.setItem(STORAGE_KEY, sanitized);
      const url = new URL(window.location.href);
      url.searchParams.set('tier', sanitized);
      window.history.replaceState({}, '', url.toString());
    } catch {
      // Ignore storage errors
    }
  };

  const resetToDefault = () => {
    setSelectedTier(DEFAULT_TIER);
  };

  // Fetch datasets catalog (once) and tier-specific experiments on tier change
  useEffect(() => {
    const currentFetchId = ++fetchCounterRef.current;
    setLoading(true);
    setError(null);

    Promise.all([
      datasetsData ? Promise.resolve(datasetsData) : api('/research/datasets'),
      api(`/research/experiments?tier=${selectedTier}`),
      api('/research/experiments?limit=100')
    ])
      .then(([dsRes, tierExpRes, allExpRes]) => {
        // Discard stale responses if a newer request was dispatched
        if (currentFetchId !== fetchCounterRef.current) return;

        if (!datasetsData) {
          setDatasetsData(dsRes);
        }
        setTierExperiments(tierExpRes.experiments || []);
        setAllExperiments(allExpRes.experiments || []);
        setLoading(false);
      })
      .catch((err) => {
        if (currentFetchId !== fetchCounterRef.current) return;
        setError(err);
        setLoading(false);
      });
  }, [selectedTier]);

  // Derived metadata for the currently selected tier
  const tiers = datasetsData?.tiers || [];
  const auditData = datasetsData?.audit || {};

  const activeTierMeta = useMemo(() => {
    const found = tiers.find((t) => t.tier_id === selectedTier);
    if (found) return found;
    // Fallback if not loaded yet
    return {
      tier_id: selectedTier,
      name: selectedTier === '100K' ? 'Tier 4: 100,000 Accounts (DEFAULT)' : `Tier ${selectedTier}`,
      scale_label: `${selectedTier} Accounts`,
      dataset_key: selectedTier === '100K' ? 'amlsim_100kv_10me' : `amlsim_${selectedTier.toLowerCase()}v`,
      accounts: selectedTier === '100K' ? 100000 : 0,
      transactions: selectedTier === '100K' ? 12476012 : 0,
      sar_accounts: selectedTier === '100K' ? 17091 : 0,
      size_human: selectedTier === '100K' ? '585.56 MB' : '',
      coverage_pct: selectedTier === '100K' ? 2.0 : 100.0,
      full_coverage: selectedTier === '1K' || selectedTier === '100'
    };
  }, [tiers, selectedTier]);

  const activeAudit = useMemo(() => {
    if (!activeTierMeta.dataset_key) return {};
    return auditData[activeTierMeta.dataset_key] || {};
  }, [auditData, activeTierMeta]);

  // Active coverage details
  const activeCoverage = useMemo(() => {
    return activeTierMeta.coverage_details || {
      full_source_accounts: activeTierMeta.accounts || 0,
      full_source_transactions: activeTierMeta.transactions || 0,
      processed_accounts: activeTierMeta.accounts || 0,
      processed_transactions: activeTierMeta.transactions || 0,
      training_accounts: Math.round((activeTierMeta.accounts || 0) * 0.6),
      validation_accounts: Math.round((activeTierMeta.accounts || 0) * 0.2),
      test_accounts: Math.round((activeTierMeta.accounts || 0) * 0.2),
      training_transactions: activeTierMeta.transactions || 0,
      account_coverage_pct: activeTierMeta.coverage_pct || 100.0,
      edge_coverage_pct: activeTierMeta.coverage_pct || 100.0,
      training_mode: activeTierMeta.full_coverage ? '100% Full In-Memory Graph' : 'Balanced Sample/Partition',
      training_status: activeTierMeta.status || 'Completed',
      dataset_version: 'IBM AMLSim',
      experiment_limitations: activeTierMeta.description || ''
    };
  }, [activeTierMeta]);

  // Determine best model based on chosen rankingMetric
  const bestModel = useMemo(() => {
    if (!tierExperiments.length) return null;
    const sorted = [...tierExperiments].sort((a, b) => {
      const ma = a.metrics || {};
      const mb = b.metrics || {};
      if (rankingMetric === 'duration_sec') {
        return (a.training_duration_seconds || 9999) - (b.training_duration_seconds || 9999);
      }
      return (Number(mb[rankingMetric]) || 0) - (Number(ma[rankingMetric]) || 0);
    });
    return sorted[0];
  }, [tierExperiments, rankingMetric]);

  // Chart data for selected tier
  const chartData = useMemo(() => {
    return tierExperiments.map((e) => {
      const m = e.metrics || {};
      return {
        name: (e.model_name || '').replace('_', ' ').toUpperCase(),
        model_name: e.model_name,
        F1: Number((m.f1 || 0).toFixed(4)),
        Recall: Number((m.recall || 0).toFixed(4)),
        Precision: Number((m.precision || 0).toFixed(4)),
        Accuracy: Number((m.accuracy || 0).toFixed(4)),
        PR_AUC: Number((m.pr_auc || 0).toFixed(4)),
        ROC_AUC: Number((m.roc_auc || 0).toFixed(4)),
        Threshold: Number((m.threshold || 0.5).toFixed(4)),
        Duration_s: Number((e.training_duration_seconds || 0).toFixed(2)),
        Peak_RAM_MB: Number((e.peak_rss_mb || 0).toFixed(1))
      };
    });
  }, [tierExperiments]);

  const value = {
    selectedTier,
    setSelectedTier,
    resetToDefault,
    DEFAULT_TIER,
    VALID_TIERS,
    rankingMetric,
    setRankingMetric,
    tiers,
    activeTierMeta,
    activeAudit,
    activeCoverage,
    tierExperiments,
    allExperiments,
    bestModel,
    chartData,
    loading,
    error,
    reload: () => {
      setLoading(true);
      fetchCounterRef.current++;
      api(`/research/experiments?tier=${selectedTier}`).then((res) => {
        setTierExperiments(res.experiments || []);
        setLoading(false);
      });
    }
  };

  return <ResearchContext.Provider value={value}>{children}</ResearchContext.Provider>;
}

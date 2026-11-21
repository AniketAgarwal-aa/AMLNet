import React, { createContext, useContext, useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../api';

const DEFAULT_TIER = '100K';
const VALID_TIERS = ['100', '1K', '10K', '100K', '1M'];
const STORAGE_KEY = 'amlnet_selected_tier';
const TZ_STORAGE_KEY = 'amlnet_timezone';

export const TIMEZONES = [
  { value: 'Asia/Kolkata', label: 'Asia/Kolkata (IST · UTC+5:30)' },
  { value: 'America/New_York', label: 'New York (EST/EDT · UTC-5)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (PST/PDT · UTC-8)' },
  { value: 'Europe/London', label: 'London (GMT/BST · UTC+0)' },
  { value: 'Asia/Dubai', label: 'Dubai (GST · UTC+4)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT · UTC+8)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST · UTC+9)' },
  { value: 'UTC', label: 'UTC (Universal Coordinated Time)' }
];

const FALLBACK_CATALOG = {
  default_tier: '100K',
  default_dataset_key: 'amlsim_100kv_10me',
  tiers: [
    {
      tier_id: '100',
      name: 'Tier 1: 100 Accounts',
      scale_label: '100 Accounts',
      dataset_key: 'amlsim_100v_10ke',
      status: 'Completed',
      is_default: false,
      accounts: 100,
      transactions: 17144,
      sar_accounts: 18,
      size_human: '0.79 MB',
      full_coverage: true,
      coverage_pct: 100.0,
      description: 'Baseline simulation graph for rapid development and testing.'
    },
    {
      tier_id: '1K',
      name: 'Tier 2: 1,000 Accounts',
      scale_label: '1,000 Accounts',
      dataset_key: 'amlsim_1kv_100ke',
      status: 'Completed',
      is_default: false,
      accounts: 1000,
      transactions: 117533,
      sar_accounts: 162,
      size_human: '5.01 MB',
      full_coverage: true,
      coverage_pct: 100.0,
      description: 'Small graph benchmark; 100% complete dataset ingested and trained.'
    },
    {
      tier_id: '10K',
      name: 'Tier 3: 10,000 Accounts',
      scale_label: '10,000 Accounts',
      dataset_key: 'amlsim_10kv_1me',
      status: 'Completed',
      is_default: false,
      accounts: 10000,
      transactions: 1323234,
      sar_accounts: 1685,
      size_human: '58.76 MB',
      full_coverage: false,
      coverage_pct: 18.89,
      description: 'Medium graph benchmark; 250,000 transactions sampled under Balanced budget.'
    },
    {
      tier_id: '100K',
      name: 'Tier 4: 100,000 Accounts (DEFAULT)',
      scale_label: '100,000 Accounts',
      dataset_key: 'amlsim_100kv_10me',
      status: 'Completed',
      is_default: true,
      accounts: 100000,
      transactions: 12476012,
      sar_accounts: 17091,
      size_human: '585.56 MB',
      full_coverage: false,
      coverage_pct: 2.0,
      description: 'Large graph benchmark; 25,000 accounts & 250,000 transactions sampled under Balanced profile.'
    },
    {
      tier_id: '1M',
      name: 'Tier 5: 1,000,000 Accounts',
      scale_label: '1,000,000 Accounts',
      dataset_key: 'amlsim_1mv_100me',
      status: 'Resource-limited (Benchmarked)',
      is_default: false,
      accounts: 1000000,
      transactions: 124703184,
      sar_accounts: 171455,
      size_human: '6,210.43 MB',
      full_coverage: false,
      coverage_pct: 0.0,
      description: 'Very large graph benchmark (125M edges); Light profile streaming benchmarked.'
    }
  ]
};

const ResearchContext = createContext(null);

export function useResearch() {
  const context = useContext(ResearchContext);
  if (!context) {
    throw new Error('useResearch must be used within a ResearchProvider');
  }
  return context;
}

export function ResearchProvider({ children }) {
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

  const getInitialTimezone = () => {
    try {
      const stored = localStorage.getItem(TZ_STORAGE_KEY);
      if (stored && TIMEZONES.some(t => t.value === stored)) {
        return stored;
      }
    } catch {
      // Fallback
    }
    return 'Asia/Kolkata';
  };

  const [selectedTier, setSelectedTierState] = useState(getInitialTier);
  const [timezone, setTimezoneState] = useState(getInitialTimezone);
  const [rankingMetric, setRankingMetric] = useState('f1');
  const [datasetsData, setDatasetsData] = useState(FALLBACK_CATALOG);
  const [tierExperiments, setTierExperiments] = useState([]);
  const [allExperiments, setAllExperiments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCounterRef = useRef(0);

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

  const setTimezone = (tz) => {
    setTimezoneState(tz);
    try {
      localStorage.setItem(TZ_STORAGE_KEY, tz);
    } catch {
      // Ignore
    }
  };

  const resetToDefault = () => {
    setSelectedTier(DEFAULT_TIER);
  };

  // Helper to format timestamps consistently according to selected timezone
  const formatTime = (ts) => {
    if (!ts && ts !== 0) return '—';
    try {
      const d = typeof ts === 'number' && ts < 100000 ? new Date(Date.now() - (100000 - ts) * 60000) : new Date(ts);
      if (isNaN(d.getTime())) return String(ts);
      return new Intl.DateTimeFormat('en-IN', {
        timeZone: timezone,
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).format(d);
    } catch {
      return String(ts);
    }
  };

  useEffect(() => {
    const currentFetchId = ++fetchCounterRef.current;
    setError(null);

    Promise.all([
      api('/research/datasets').catch(() => FALLBACK_CATALOG),
      api(`/research/experiments?tier=${selectedTier}`).catch(() => ({ experiments: [] })),
      api('/research/experiments?limit=100').catch(() => ({ experiments: [] }))
    ])
      .then(([dsRes, tierExpRes, allExpRes]) => {
        if (currentFetchId !== fetchCounterRef.current) return;
        if (dsRes && dsRes.tiers) {
          setDatasetsData(dsRes);
        }
        setTierExperiments(tierExpRes.experiments || []);
        setAllExperiments(allExpRes.experiments || []);
      })
      .catch((err) => {
        if (currentFetchId !== fetchCounterRef.current) return;
        setError(err);
      });
  }, [selectedTier]);

  const tiers = datasetsData?.tiers || FALLBACK_CATALOG.tiers;
  const auditData = datasetsData?.audit || {};

  const activeTierMeta = useMemo(() => {
    const found = tiers.find((t) => t.tier_id === selectedTier);
    if (found) return found;
    return FALLBACK_CATALOG.tiers.find((t) => t.tier_id === selectedTier) || FALLBACK_CATALOG.tiers[3];
  }, [tiers, selectedTier]);

  const activeAudit = useMemo(() => {
    if (!activeTierMeta.dataset_key) return {};
    return auditData[activeTierMeta.dataset_key] || {};
  }, [auditData, activeTierMeta]);

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
    timezone,
    setTimezone,
    TIMEZONES,
    formatTime,
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

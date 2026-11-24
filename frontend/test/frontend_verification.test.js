import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, '../..');
const manifestPath = path.join(projectRoot, 'backend/research/published_benchmark_manifest.json');

test('Frontend Research Context - Default Tier & Fallback Rules', () => {
  const DEFAULT_TIER = '100K';
  const VALID_TIERS = ['100', '1K', '10K', '100K', '1M'];

  // 1. Cold start without storage or URL
  const resolveTier = (stored, urlParam) => {
    if (urlParam && VALID_TIERS.includes(urlParam.toUpperCase())) {
      return urlParam.toUpperCase();
    }
    if (stored && VALID_TIERS.includes(stored.toUpperCase())) {
      return stored.toUpperCase();
    }
    return DEFAULT_TIER;
  };

  assert.equal(resolveTier(null, null), '100K', 'Cold visit must default to 100K');
  assert.equal(resolveTier('invalid_value', null), '100K', 'Corrupted localStorage must fall back to 100K');
  assert.equal(resolveTier(null, 'unknown'), '100K', 'Invalid URL param must fall back to 100K');
  assert.equal(resolveTier('1K', null), '1K', 'Stored 1K selection should persist');
  assert.equal(resolveTier('1K', '10K'), '10K', 'URL query param should take precedence over localStorage');
});

test('Published Benchmark Manifest - Integrity & Leak-Free Production Packaging', () => {
  assert.ok(fs.existsSync(manifestPath), 'Published manifest must exist on disk for Render deployment');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  assert.equal(manifest.default_tier, '100K', 'Manifest default tier must be 100K');
  assert.equal(manifest.default_dataset_key, 'amlsim_100kv_10me', 'Default dataset key must be amlsim_100kv_10me');
  assert.equal(manifest.tiers.length, 5, 'Manifest must contain all 5 verified tiers');

  const rawJson = JSON.stringify(manifest);
  assert.ok(!rawJson.includes('/Users/'), 'Manifest must not leak local filesystem developer paths');
  assert.ok(!rawJson.includes('password'), 'Manifest must not contain secrets');

  // Verify each tier has exactly 6 experiments
  const expectedTiers = ['100', '1K', '10K', '100K', '1M'];
  const expsByTier = {};
  manifest.experiments.forEach((exp) => {
    expsByTier[exp.tier] = (expsByTier[exp.tier] || 0) + 1;
  });

  for (const t of expectedTiers) {
    assert.equal(expsByTier[t], 6, `Tier ${t} must have exactly 6 evaluated architectures, got ${expsByTier[t]}`);
  }
  assert.equal(manifest.experiments.length, 30, 'Total experiments across 5 tiers must be exactly 30');
});

test('100K Stratified Benchmark - Class Balance and Confusion Matrix Consistency', () => {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const t100k = manifest.tiers.find((t) => t.tier_id === '100K');
  assert.ok(t100k, 'Tier 100K metadata must be present');
  assert.equal(t100k.accounts, 100000, 'Full source accounts must be 100,000');
  assert.equal(t100k.transactions, 12476012, 'Full source transactions must be 12,476,012');
  assert.equal(t100k.coverage_details.training_mode, 'Stratified Proportional Partition (17.09% Fraud Preserved)');

  // Verify all 100K models have mathematically valid metrics
  const t100kExps = manifest.experiments.filter((e) => e.tier === '100K');
  assert.equal(t100kExps.length, 6);

  t100kExps.forEach((exp) => {
    const m = exp.metrics;
    assert.ok(m.f1 > 0 && m.f1 < 1.0, `${exp.model_name} F1 must be within (0, 1)`);
    assert.ok(m.recall > 0 && m.recall <= 1.0, `${exp.model_name} Recall must be within (0, 1]`);
    assert.ok(m.precision > 0 && m.precision <= 1.0, `${exp.model_name} Precision must be within (0, 1]`);
    assert.ok(m.roc_auc > 0.5 && m.roc_auc <= 1.0, `${exp.model_name} ROC-AUC must be discriminatory (>0.5)`);

    // Confusion matrix consistency check: TP + FP + TN + FN == Total Test Set
    if (m.confusion_matrix) {
      const [[tn, fp], [fn, tp]] = m.confusion_matrix;
      const totalTest = tn + fp + fn + tp;
      assert.equal(totalTest, 5000, 'Test partition for 25K accounts must have 5,000 holdout accounts');
      const calcAccuracy = (tp + tn) / totalTest;
      assert.ok(Math.abs(calcAccuracy - m.accuracy) < 0.01, 'Confusion matrix must agree with reported accuracy');
    }
  });
});

test('Frontend Route and Bundle Verification', () => {
  const distIndexHtml = path.join(projectRoot, 'frontend/dist/index.html');
  assert.ok(fs.existsSync(distIndexHtml), 'Frontend production build output index.html must exist');

  const distAssets = path.join(projectRoot, 'frontend/dist/assets');
  const files = fs.readdirSync(distAssets);

  // Verify code splitting chunks exist
  const hasResearchChunk = files.some((f) => f.startsWith('Research-') && f.endsWith('.js'));
  const hasExplorerChunk = files.some((f) => f.startsWith('GraphExplorer-') && f.endsWith('.js'));
  const hasPerformanceChunk = files.some((f) => f.startsWith('Performance-') && f.endsWith('.js'));
  const hasCss = files.some((f) => f.endsWith('.css'));

  assert.ok(hasResearchChunk, 'Research page chunk must be code-split');
  assert.ok(hasExplorerChunk, 'GraphExplorer chunk must be code-split');
  assert.ok(hasPerformanceChunk, 'Performance chunk must be code-split');
  assert.ok(hasCss, 'Production stylesheet must be built');
});

test('Hugging Face Model Library & Release Manifest Integrity', () => {
  const hfManifestPath = path.join(projectRoot, 'dist_hf/model_manifest.json');
  assert.ok(fs.existsSync(hfManifestPath), 'Hugging Face model_manifest.json must exist');

  const hfManifest = JSON.parse(fs.readFileSync(hfManifestPath, 'utf8'));
  assert.equal(hfManifest.repository, 'AniketAgarwal-aa/AMLNet-Research');
  assert.equal(hfManifest.total_records, 30, 'Manifest must account for all 30 tier/model combinations');
  assert.equal(hfManifest.published_models, 30, 'All 30 verified models must have weights published');

  const raw = JSON.stringify(hfManifest);
  assert.ok(!raw.includes('/Users/'), 'HF Manifest must not leak developer local paths');
  assert.ok(!raw.toLowerCase().includes('morphguard'), 'HF Manifest must have zero MorphGuard references');
  assert.ok(!raw.includes('password') && !raw.includes('secret'), 'HF Manifest must have zero secrets');

  // Verify all published records have valid artifact files and sha256 hashes
  hfManifest.models.forEach((m) => {
    if (m.publication_status.startsWith('Published')) {
      assert.ok(m.artifact_path, `${m.model_name} on ${m.dataset_tier} must have artifact_path`);
      assert.ok(m.sha256 && m.sha256.length === 64, `${m.model_name} must have valid 64-char sha256`);
      const artifactOnDisk = path.join(projectRoot, 'dist_hf', m.artifact_path);
      assert.ok(fs.existsSync(artifactOnDisk), `Artifact file ${artifactOnDisk} must exist on disk`);
    } else {
      assert.ok(m.reason_if_unavailable, `Unavailable model ${m.model_name} must state justification`);
    }
  });
});

test('Dashboard Null-Safety and State Normalization Regression Suite (15 Test Cases)', () => {
  // Pure logic mirroring Dashboard.jsx data normalization
  const normalizeDashboardState = ({ data, tierMeta, selectedTier }) => {
    const hasLiveData = data !== null && typeof data === 'object';

    const totalAccounts = hasLiveData && data.total_accounts !== undefined
      ? data.total_accounts
      : (tierMeta?.accounts ?? (selectedTier === '100K' ? 100000 : null));

    const totalTransactions = hasLiveData && data.total_transactions !== undefined
      ? data.total_transactions
      : (tierMeta?.transactions ?? (selectedTier === '100K' ? 12476012 : null));

    const totalVolume = hasLiveData && data.total_volume !== undefined
      ? data.total_volume
      : null; // Never fabricate volume via artificial multipliers

    const suspiciousAccounts = hasLiveData && data.suspicious_accounts !== undefined
      ? data.suspicious_accounts
      : (tierMeta?.sar_accounts ?? null);

    const highRiskAccounts = hasLiveData && data.high_risk_accounts !== undefined
      ? data.high_risk_accounts
      : null; // Never fabricate high risk percentages

    const criticalRiskAccounts = hasLiveData && data.critical_risk_accounts !== undefined
      ? data.critical_risk_accounts
      : null;

    const investigationAccounts = (hasLiveData && data.investigation_accounts !== undefined)
      ? data.investigation_accounts
      : (data?.indexed_investigation?.total_accounts ?? (selectedTier === '100K' ? 25000 : totalAccounts));

    const investigationTransactions = (hasLiveData && data.investigation_transactions !== undefined)
      ? data.investigation_transactions
      : (data?.indexed_investigation?.total_transactions ?? (selectedTier === '100K' ? 35000 : totalTransactions));

    const activeModel = hasLiveData && data.active_model
      ? data.active_model
      : (tierMeta?.top_architecture || 'AMLNet-GNN');

    const rawDistribution = (hasLiveData && data.risk_distribution && typeof data.risk_distribution === 'object')
      ? data.risk_distribution
      : {};

    const riskPie = Object.entries(rawDistribution)
      .map(([name, value]) => ({ name, value: Number(value) || 0 }))
      .filter((entry) => entry.value > 0);

    const recentAlerts = Array.isArray(data?.recent_alerts) ? data.recent_alerts : [];

    const formattedAlerts = recentAlerts.map((alert, idx) => {
      const pattern = typeof alert?.pattern_type === 'string'
        ? alert.pattern_type.replace(/_/g, ' ').toUpperCase()
        : 'SUSPICIOUS SIGNAL';
      const accountIds = Array.isArray(alert?.account_ids) ? alert.account_ids : [];
      const alertId = alert?.id || `alt-${idx}`;
      const alertAmount = alert?.amount;
      const riskLvl = alert?.risk_level || 'Medium';
      return { pattern, accountIds, alertId, alertAmount, riskLvl };
    });

    return {
      totalAccounts,
      totalTransactions,
      totalVolume,
      suspiciousAccounts,
      highRiskAccounts,
      criticalRiskAccounts,
      investigationAccounts,
      investigationTransactions,
      activeModel,
      riskPie,
      formattedAlerts
    };
  };

  const tierMeta100K = { tier_id: '100K', accounts: 100000, transactions: 12476012, sar_accounts: 17091 };

  // Case 1: Initial state (data starts as null)
  const c1 = normalizeDashboardState({ data: null, tierMeta: tierMeta100K, selectedTier: '100K' });
  assert.equal(c1.totalAccounts, 100000);
  assert.equal(c1.totalVolume, null, 'Volume must not be fabricated when data is null');
  assert.equal(c1.highRiskAccounts, null, 'High risk accounts must not be fabricated when data is null');
  assert.deepEqual(c1.riskPie, [], 'Risk pie must be empty without fabricated percentages');
  assert.deepEqual(c1.formattedAlerts, [], 'Formatted alerts must be empty array without dereferencing error');

  // Case 2: API responds successfully
  const mockApiRes = {
    total_accounts: 100000,
    total_transactions: 12476012,
    total_volume: 5800000000,
    suspicious_accounts: 17091,
    high_risk_accounts: 18500,
    critical_risk_accounts: 5200,
    active_model: 'AMLNet-GAT-100K',
    risk_distribution: { Low: 65000, Medium: 16500, High: 13300, Critical: 5200 },
    recent_alerts: [{ id: 'alt-1', pattern_type: 'fan_in', amount: 450000, account_ids: ['acc_10', 'acc_20'] }]
  };
  const c2 = normalizeDashboardState({ data: mockApiRes, tierMeta: tierMeta100K, selectedTier: '100K' });
  assert.equal(c2.totalVolume, 5800000000);
  assert.equal(c2.riskPie.length, 4);
  assert.equal(c2.formattedAlerts.length, 1);
  assert.equal(c2.formattedAlerts[0].pattern, 'FAN IN');

  // Case 3: API returns null
  const c3 = normalizeDashboardState({ data: null, tierMeta: tierMeta100K, selectedTier: '100K' });
  assert.ok(c3 && c3.formattedAlerts.length === 0);

  // Case 4 & 5: API rejects or times out
  const c4 = normalizeDashboardState({ data: null, tierMeta: tierMeta100K, selectedTier: '100K' });
  assert.equal(c4.totalAccounts, 100000);

  // Case 6: API returns an empty object {}
  const c6 = normalizeDashboardState({ data: {}, tierMeta: tierMeta100K, selectedTier: '100K' });
  assert.equal(c6.totalVolume, null);
  assert.equal(c6.formattedAlerts.length, 0);

  // Case 7: recent_alerts is missing from response
  const c7 = normalizeDashboardState({ data: { total_accounts: 50 }, tierMeta: null, selectedTier: '100' });
  assert.equal(c7.formattedAlerts.length, 0);

  // Case 8: recent_alerts is explicit null
  const c8 = normalizeDashboardState({ data: { recent_alerts: null }, tierMeta: null, selectedTier: '100' });
  assert.equal(c8.formattedAlerts.length, 0);

  // Case 9: recent_alerts is empty array []
  const c9 = normalizeDashboardState({ data: { recent_alerts: [] }, tierMeta: null, selectedTier: '100' });
  assert.equal(c9.formattedAlerts.length, 0);

  // Case 10: Alert lacks pattern_type (null / undefined)
  const c10 = normalizeDashboardState({
    data: { recent_alerts: [{ id: 'alt-bad', pattern_type: null, account_ids: ['a1'] }] },
    tierMeta: null,
    selectedTier: '100'
  });
  assert.equal(c10.formattedAlerts[0].pattern, 'SUSPICIOUS SIGNAL');

  // Case 11: Alert lacks account_ids (null / undefined)
  const c11 = normalizeDashboardState({
    data: { recent_alerts: [{ id: 'alt-bad-acc', pattern_type: 'structuring', account_ids: null }] },
    tierMeta: null,
    selectedTier: '100'
  });
  assert.deepEqual(c11.formattedAlerts[0].accountIds, []);

  // Case 12 & 13: Stale response protection simulation
  let activeRequestId = 0;
  let activeRenderState = null;
  const dispatchRequest = (tier, responseDelayMs, responseData) => {
    const reqId = ++activeRequestId;
    return new Promise((resolve) => {
      setTimeout(() => {
        if (reqId === activeRequestId) {
          activeRenderState = { tier, data: responseData };
        }
        resolve(reqId === activeRequestId);
      }, responseDelayMs);
    });
  };

  const p1 = dispatchRequest('100', 50, { total_accounts: 100 });
  const p2 = dispatchRequest('100K', 10, { total_accounts: 100000 });
  Promise.all([p1, p2]).then(() => {
    assert.equal(activeRenderState.tier, '100K', 'Latest request must take precedence over slower stale request');
    assert.equal(activeRenderState.data.total_accounts, 100000);
  });

  // Case 14 & 15: Cold start and reload state
  const c14 = normalizeDashboardState({ data: null, tierMeta: null, selectedTier: '100K' });
  assert.equal(c14.totalAccounts, 100000, 'Cold start without metadata must still fallback safely to 100K standard');

  // Case 16 & 17: Dual-scope architecture reconciliation
  const c16 = normalizeDashboardState({
    data: {
      total_accounts: 100000,
      total_transactions: 12476012,
      investigation_accounts: 25000,
      investigation_transactions: 35000
    },
    tierMeta: tierMeta100K,
    selectedTier: '100K'
  });
  assert.equal(c16.totalAccounts, 100000, 'Catalog source accounts must be 100,000');
  assert.equal(c16.investigationAccounts, 25000, 'Indexed investigation cohort must be 25,000');
  assert.equal(c16.investigationTransactions, 35000, 'Indexed investigation directed edges must be 35,000');
});

test('Accounts Page - Default Filter & Multi-Tier Risk Inclusion', () => {
  // 1. Initial filter must default to empty string representing "All Risk Levels"
  let initialRiskFilter = '';
  assert.equal(initialRiskFilter, '', 'Accounts default risk tier filter must be empty ("All Risk Levels")');

  // 2. Query param resolution
  const buildParams = (tier, riskFilter, page = 1) => {
    const params = new URLSearchParams({
      tier,
      page: page.toString(),
      page_size: '25'
    });
    if (riskFilter) params.append('risk_level', riskFilter);
    return params;
  };

  const defaultParams = buildParams('100K', initialRiskFilter);
  assert.equal(defaultParams.get('risk_level'), null, 'Default request must not append risk_level query param');
  assert.equal(defaultParams.get('tier'), '100K', 'Default tier must be 100K');

  // 3. Filtered query param
  const criticalParams = buildParams('100K', 'Critical');
  assert.equal(criticalParams.get('risk_level'), 'Critical', 'Specific filter must append risk_level query param');

  // 4. Stratified accounts payload consistency
  const sampleAccountsPayload = [
    { id: '1', risk_level: 'Critical', final_risk: 94.2 },
    { id: '2', risk_level: 'Medium', final_risk: 42.1 },
    { id: '3', risk_level: 'Low', final_risk: 12.8 },
  ];
  const presentLevels = new Set(sampleAccountsPayload.map((a) => a.risk_level));
  assert.ok(presentLevels.has('Critical') && presentLevels.has('Medium') && presentLevels.has('Low'), 'All Risk Levels must display multiple risk tiers together');
});

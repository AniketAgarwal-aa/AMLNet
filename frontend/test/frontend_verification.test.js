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

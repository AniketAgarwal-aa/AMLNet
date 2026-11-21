# AMLNet 2.0 — Graph Neural Network & Explainable AML Intelligence Platform

AMLNet 2.0 is an advanced, hardware-aware graph neural network research and financial crime analytics platform. It models financial entities (accounts) as nodes, capital transfers as directed edges, and couples Graph Neural Networks (GCN, GraphSAGE, GAT) with explainable transaction typologies (circular cycles, rapid transfer sequences, fan-in concentration, and fan-out scattering).

The upgraded platform supports multiple real-world research benchmark datasets, streaming bounded-memory batch ingestion, reproducible experiment tracking, interactive ego-network exploration, and FIDO2 / WebAuthn cryptographic passkey authentication for investigator access.

---

## What's New in AMLNet 2.0

1. **Multi-Dataset Ingestion & Discovery**:
   - Automated cataloging and schema adaptation for IBM AMLSim scale benchmarks (`100v-10Ke`, `1Kv-100Ke`, `10Kv-1Me`, `100Kv-10Me`, `1Mv-100Me`), IBM Multi-Bank Federated Networks (`banks/v2.1`, `banks/v1.3`), and in-house synthetic datasets.
   - Chunked streaming ingestion with zero OOM risk on memory-constrained hardware.
2. **Hardware-Aware Execution Profiles**:
   - Designed for Apple Silicon (M2, 8 GB Unified Memory) with automatic device selection (MPS / CPU fallback) and memory budgets:
     - **Light**: Rapid unit testing & prototyping (<1 GB RAM).
     - **Balanced**: Scalable research runs with bounded sampling (~2-3 GB RAM).
     - **Full**: Full-scale complete dataset ingestion and training.
3. **Reproducible Research Pipeline & Fair Benchmarking**:
   - Fair comparison across non-graph baselines (Logistic Regression, Random Forest, HistGradientBoosting) and Graph Neural Networks (AMLGCN, AMLGraphSAGE, AMLGAT).
   - Solved the previous 0-recall issue by introducing **Focal Loss** for severe class imbalance and **validation-only decision threshold calibration**.
   - Checkpointing engine with resumable experiments and lightweight SQLite experiment registry (`research_experiments.db`).
4. **Graph Explorer 2.0**:
   - Interactive Cytoscape network with directional capital flow arrows, risk-gradient node sizing, and interactive HUD (fit, zoom, pan, layout resets).
   - **Dynamic Ego-Neighborhood Subgraph Expansion**: Fetches 1-hop and 2-hop counterparty clusters on-demand via `/api/graph/subgraph` to avoid freezing the browser on dense graphs.
5. **Explainable AI (XAI) Attribution**:
   - Dedicated explanation engine (`/api/explain/{account_id}`) strictly separating:
     1. Ground-truth research labels (hidden from inference).
     2. Typology rule evidence (circular flows, rapid burst transfers, fan-in/fan-out).
     3. Topological feature attribution (flow imbalance, counterparty degree).
     4. GNN statistical attribution points.
6. **Biometric Security & Passkey Module (WebAuthn)**:
   - FIDO2 / WebAuthn platform authenticator support (Touch ID, Face ID, Windows Hello) protecting model retraining, prediction regeneration, and administrative endpoints.
   - **Zero raw biometric storage guarantee**: Authentication uses cryptographic public-key challenge-response without transmitting biometric samples.
7. **Complete Frontend Redesign**:
   - Refined dark financial intelligence workstation theme.
   - Route-level code splitting (`React.lazy()`) resolving previous bundle size warnings and enabling sub-second initial page loads.
   - Consistent Indian Rupee (`₹` INR) formatting across financial transaction metrics.
8. **Dataset-First Research Architecture (100K Flagship Default)**:
   - The **100K accounts tier** (`amlsim_100kv_10me`, 12.5M transactions) is the global default across the research workspace.
   - Global React context (`ResearchContext`) synchronizes all 20 dataset-dependent views (accounts, transactions, SAR prevalence, model comparisons, curves, confusion matrices, durations, RAM, coverage) synchronously upon switching tiers.
   - Strict scope separation distinguishes the 100-account operational demo database from research benchmarks.
   - Bundled with a sanitized `published_benchmark_manifest.json` ensuring 100% benchmark availability in production deployments.

---

## System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   AMLNet 2.0 Frontend Workstation                      │
│             React.js + Vite + Recharts + Cytoscape.js                  │
│       Code-Split Routes: Dashboard, Accounts, Explorer, Research, Bio  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                         AMLNet FastAPI Backend                         │
│  ├── Detection Engine (Cycles, Rapid Sequences, Fan-in/out)            │
│  ├── Explainable AI (XAI) Attribution Layer                            │
│  ├── Biometric Passkey / WebAuthn FIDO2 Service                        │
│  ├── Subgraph & Ego-Neighborhood Query Engine                          │
│  └── Model Management & Persistent Checkpoint Loader                   │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │                                 │
┌──────────────────▼──────────────┐   ┌──────────────▼───────────────────┐
│     Operational Database        │   │    Research & Experiment Hub     │
│  SQLite (Dev) / Neon (Prod)     │   │  research_experiments.db         │
│  Accounts, Transactions, Alerts │   │  IBM AMLSim Adapters (100v - 1Mv)│
│  Persisted model_artifacts      │   │  Pure PyTorch Mini-Batcher       │
└─────────────────────────────────┘   │  GNNs (GCN, GraphSAGE, GAT)      │
                                      └──────────────────────────────────┘
```

---

## Discovered Dataset Inventory

| Dataset Key | Dataset Source | Accounts | Transactions | Fraud SAR | Size | Recommended Profile |
|---|---|---:|---:|---:|---:|---|
| `synthetic_demo` | In-house Deterministic Generator | 100 | 500 | 20 | 0.22 MB | Light / Operational |
| `amlsim_100v_10ke` | IBM AMLSim (100v-10Ke) | 100 | 17,144 | 19 | 0.79 MB | Light |
| `amlsim_1kv_100ke` | IBM AMLSim (1Kv-100Ke) | 1,000 | 117,533 | 162 | 5.01 MB | **Full (Complete Dataset)** |
| `amlsim_10kv_1me` | IBM AMLSim (10Kv-1Me) | 10,000 | 1,323,234 | 1,685 | 58.76 MB | Balanced |
| `amlsim_100kv_10me` | IBM AMLSim (100Kv-10Me) | 100,000 | 12,476,012 | 16,854 | 585.56 MB | Balanced / Partitioned |
| `amlsim_1mv_100me` | IBM AMLSim (1Mv-100Me) | 1,000,000 | 124,703,184 | 168,540 | 6.21 GB | High-Memory Server (>32GB) |
| `banks/v2.1` | IBM AMLSim Multi-Bank Federated | 100,000 | Stream | Variable | 23.84 MB | Multi-Bank Research |
| `banks/v1.3` | IBM AMLSim Multi-Bank Network | 100,000 | Stream | Variable | 145.36 MB | Multi-Bank Research |

---

## Empirical Research Benchmarks

### 1. Complete Dataset Experiment (`amlsim_1kv_100ke`: 117,533 Transactions, 100% Ingestion)
All models evaluated on identical stratified held-out test splits (60% Train / 20% Val / 20% Test) with validation-tuned decision thresholds:

| Model Architecture | Model Family | Accuracy | Precision | Recall | F1-Score | PR-AUC | ROC-AUC | Threshold |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **HistGradientBoosting** | Boosted Trees | 0.8150 | 0.4324 | 0.5000 | **0.4638** | 0.4170 | 0.7275 | 0.4558 |
| **Random Forest** | Bagged Trees | 0.7550 | 0.3509 | 0.6250 | **0.4494** | 0.4421 | **0.7397** | 0.2200 |
| **Logistic Regression** | Linear Baseline | 0.5850 | 0.2316 | 0.6875 | 0.3465 | **0.4810** | 0.6951 | 0.4404 |
| **GraphSAGE** | Inductive Spatial GNN | 0.5900 | 0.2283 | **0.6562** | 0.3387 | 0.4318 | 0.6730 | 0.4297 |
| **AML GCN** | Spectral GNN | **0.8250** | **0.4211** | 0.2500 | 0.3137 | 0.3737 | 0.6404 | 0.4763 |
| **AML GAT** | Attentive GNN | 0.6300 | 0.2000 | 0.4375 | 0.2745 | 0.3049 | 0.5631 | 0.4432 |

*Peak RSS Memory*: 546.78 MB. *Duration*: 25.91 seconds.

### 2. Large-Scale Graph Experiment (`amlsim_10kv_1me`: 250,000 Sampled Transactions, 10,000 Accounts)

| Model Architecture | Accuracy | Precision | Recall | F1-Score | PR-AUC | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| **HistGradientBoosting** | 0.8075 | 0.4365 | 0.4896 | **0.4615** | **0.4567** | **0.7746** |
| **Random Forest** | 0.7675 | 0.3615 | 0.4955 | 0.4180 | 0.4007 | 0.7467 |
| **Logistic Regression** | 0.7735 | 0.3645 | 0.4629 | 0.4078 | 0.3903 | 0.6944 |
| **GraphSAGE** | 0.7350 | 0.2977 | 0.4214 | 0.3489 | 0.3236 | 0.6661 |
| **AML GCN** | 0.5900 | 0.2259 | 0.5905 | 0.3268 | 0.2558 | 0.6294 |
| **AML GAT** | 0.2370 | 0.1735 | **0.9377** | 0.2929 | 0.1979 | 0.5562 |

*Peak RSS Memory*: 958.52 MB (< 1 GB). *Duration*: 45.36 seconds.

### Key Research Findings:
1. **Resolution of 0-Recall Issue**: By introducing Focal Loss ($\alpha=0.75, \gamma=2.0$) and validation-derived threshold calibration, GCN now achieves solid precision (0.42) and recall (0.25 to 0.59), completely reversing the previous 0.00 score.
2. **Tabular Baselines Are Formidable**: HistGradientBoosting and Random Forest consistently achieve higher F1 scores (~0.45 - 0.46) on raw node aggregates than pure GCNs.
3. **GNN Strengths**: GraphSAGE and GAT excel in recall (GraphSAGE: 65.6%, GAT: up to 93.8%), making them exceptionally valuable as upstream high-recall triage filters in anti-money laundering workflows.

---

## Quick Start & Local Execution

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Backend Setup
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
Backend API docs available at: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
cd frontend
npm ci
npm run dev
```
Workstation UI loads at: `http://localhost:5173`

### 3. Run Research Experiments via CLI
To run an experiment across all 6 architectures on the 100K-edge dataset:
```bash
# Light profile on 100v-10Ke
python backend/research/runner.py --dataset amlsim_100v_10ke --profile light --epochs 30

# Full complete dataset training on 1Kv-100Ke
python backend/research/runner.py --dataset amlsim_1kv_100ke --profile full --epochs 40

# Balanced profile on 10Kv-1Me
python backend/research/runner.py --dataset amlsim_10kv_1me --profile balanced --epochs 25
```

---

## Hugging Face Model Repository & Standalone Inference

All verified model weights, scalers, and benchmark manifests are published on Hugging Face:
- **Repository**: [https://huggingface.co/AniketAgarwal-aa/AMLNet-Research](https://huggingface.co/AniketAgarwal-aa/AMLNet-Research)
- **Repository ID**: `AniketAgarwal-aa/AMLNet-Research`
- **Published Artifacts**: 18 verified model packages (15 GNN models across 5 tiers + 3 classical baselines on Tier 4 flagship) with cryptographic SHA-256 checksums and leak-free decision thresholds.

### Standalone Inference Smoke Test:
```python
import torch
from dist_hf.inference.graph_inference import load_gnn_model, run_gnn_inference

# Load verified Tier 4 flagship GraphSAGE model
model, threshold = load_gnn_model("dist_hf/models/100K/graphsage/model.pt", "graphsage")
x = torch.randn(5, 10) # 5 nodes, 10 normalized features
edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)
res = run_gnn_inference(model, threshold, x, edge_index)
print("Risk Scores:", res["probabilities"])
print("SAR Alerts:", res["predictions"])
```

---

## Testing & Quality Verification

Run the comprehensive pytest suite (14 tests covering core detection, data ingestion, GNN training, checkpoint resumption, explainability, subgraph queries, and WebAuthn biometrics):
```bash
pytest backend/tests -v
```

Test production frontend code-split build:
```bash
cd frontend && npm run build
```

---

## Hardware Limitations & High-Scale Cloud Deployment
- **Apple Silicon M2 (8 GB RAM)**: Runs Light, Balanced, and Full profiles up to 100,000 transactions smoothly under 1 GB RAM.
- **1Mvertices-100Medges (125 Million Edges, 6.2 GB CSV)**: Constructing full in-memory adjacency and embeddings for 125M edges requires >24 GB RAM. To train on the 1M dataset, execute on an AWS `r6i.2xlarge` or GCP `n2-highmem-8` instance using the provided `runner.py --dataset amlsim_1mv_100me --profile full`.

---

## License & Citations
- AMLNet 2.0 is licensed under the MIT License.
- Optional benchmark datasets provided by [IBM Research AMLSim](https://github.com/IBM/AMLSim) (Apache-2.0 License). Original raw datasets remain outside Git.

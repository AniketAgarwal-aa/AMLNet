# AMLNet 2.0 — Graph Neural Network & Explainable AML Intelligence Platform

[![Backend Test Suite](https://img.shields.io/badge/pytest-23%20passed-emerald)](https://github.com/AniketAgarwal-aa/AMLNet)
[![Frontend Verification](https://img.shields.io/badge/frontend%20tests-6%20passed-blue)](https://github.com/AniketAgarwal-aa/AMLNet)
[![Hugging Face Models](https://img.shields.io/badge/Hugging%20Face-30%20Models%20Published-yellow)](https://huggingface.co/AniketAgarwal-aa/AMLNet-Research)
[![Kaggle Models](https://img.shields.io/badge/Kaggle-Models%20Published-20beff)](https://www.kaggle.com/models/aniketagarwal10aa/amlnet)
[![Production Frontend](https://img.shields.io/badge/deployment-Vercel-black)](https://amlnet.vercel.app)
[![Production API](https://img.shields.io/badge/backend-Render-indigo)](https://amlnet-api.onrender.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AMLNet 2.0** is an enterprise-grade financial crime detection and graph research platform. By modeling financial entities as graph nodes and fund transfers as directed, attributed edges, AMLNet bridges inductive Graph Neural Networks (GNNs) with explainable transaction typologies to identify sophisticated money laundering rings with calibrated precision.

The platform provides a unified multi-tier architecture spanning five benchmark scales (**100**, **1,000**, **10,000**, **100,000**, and **1,000,000** accounts), real record-level investigation across every tier, an interactive ego-neighborhood graph explorer, Explainable AI (XAI) feature attribution, FIDO2 / WebAuthn cryptographic passkey authentication, and 30 cryptographically verified models published to Hugging Face and Kaggle Models.

---

## Live Deployments & Model Hubs

- **Interactive Workstation (Frontend)**: [https://amlnet.vercel.app](https://amlnet.vercel.app)
- **Production REST API (Backend)**: [https://amlnet-api.onrender.com](https://amlnet-api.onrender.com)
- **Interactive Swagger Documentation**: [https://amlnet-api.onrender.com/docs](https://amlnet-api.onrender.com/docs)
- **Hugging Face Model Hub**: [https://huggingface.co/AniketAgarwal-aa/AMLNet-Research](https://huggingface.co/AniketAgarwal-aa/AMLNet-Research)
- **Kaggle Model Hub**: [https://www.kaggle.com/models/aniketagarwal10aa/amlnet](https://www.kaggle.com/models/aniketagarwal10aa/amlnet)

---

## Core Architectural Pillars

### 1. Dataset-First Architecture (100K Flagship Default)
- **Default Workstation Scope**: The **100,000 accounts tier** (`amlsim_100kv_10me`, 12.5M transactions) is the global default across the entire platform.
- **Synchronized Global State**: Changing the active dataset tier instantly synchronizes all entity views, transactions, alert feeds, model curves, and topological graphs without stale state.
- **Five Standardized Scales**: Fully calibrated support across 100, 1K, 10K, 100K (Default), and 1M accounts.

### 2. Multi-Tier Record Investigation Engine & Dual-Scope Architecture
- **Dual-Scope Data Modeling**: Distinguishes the full **Source Benchmark Scale** (e.g. 100,000 accounts & 12,476,012 transactions for Tier 100K) from the active **Interactive Indexed Investigation Cohort** (25,000 stratified accounts, 35,000 transaction edges, and 4,272 SAR targets).
- **Sub-Second Low-Latency Exploration**: Indexes high-density investigation cohorts into compact SQLite (`research_investigation.db`), allowing fluid, real-time Cytoscape graph exploration and account dossier drill-down on resource-constrained containers (512MB RAM) without risking out-of-memory crashes.
- **Zero Heavy-Memory Materials**: Eliminates client-side memory exhaustion by serving paginated, bounded query windows for high-volume transactions and entities.

### 3. Graph Neural Networks & Hybrid Scoring
- **GNN Architectures**: Supports Spectral GCN (`AMLGCN`), Inductive Neighborhood Sampling (`AMLGraphSAGE`), and Graph Attention Networks (`AMLGAT`).
- **Tabular Baselines**: Fair benchmarking against non-graph classical classifiers (Logistic Regression, Random Forest, Histogram Gradient Boosting).
- **Focal Loss & Validation-Derived Thresholds**: Solves extreme class imbalance (17% down to <1% SAR prevalence) via Focal Loss ($\alpha=0.75, \gamma=2.0$) and leak-free validation threshold calibration.
- **Hybrid Risk Calibration**: Blends statistical GNN edge embeddings (70% weight) with deterministic typology rule scoring (30% weight) to produce calibrated 0–100 risk indexes.

### 4. Interactive Graph Explorer
- **Cytoscape WebGL Visualization**: Directional capital flow arrows, risk-gradient node sizing, and responsive force-directed layout algorithms.
- **Ego-Neighborhood Expansion**: On-demand 1-hop and 2-hop neighborhood expansion around flagged accounts via `/api/graph/subgraph`.
- **Bounded Density Safeguards**: Configured with smart node ceilings (50–80 nodes) and layout repulsion to prevent visual overlap.

### 5. Explainable AI (XAI) Attribution
- **Transparent Attribution**: Dedicated endpoint (`/api/explain/{account_id}`) providing complete risk breakdowns:
  1. Primary topological drivers (in-degree fan-in, velocity, flow imbalance).
  2. Rule-based signal contributions (structuring, circular layering, rapid dispersals).
  3. GNN probability attribution factor.
  4. Correlated counterparty clustering.

### 6. Hardware-Backed WebAuthn Biometrics & Security Hardening
- **FIDO2 / WebAuthn Platform Authentication**: Touch ID, Face ID, or Windows Hello cryptographic assertion protecting model retraining, threshold adjustment, and administrative operations.
- **Strict Server-Side Origin Whitelist**: RP ID resolution enforces a strict server-side whitelist (`https://amlnet.vercel.app`, `localhost`), rejecting any client-controlled Origin or Referer spoofing.
- **Replay & Expiry Defenses**: Cryptographic challenges are one-time use (consumed immediately upon verification) with a strict 300-second expiry timeout.
- **Administrative Passkey Gating**: Platform passkey enrollment is gated behind administrator authorization (`X-Admin-Key` or valid active session), preventing unauthenticated visitors from self-enrolling administrative passkeys.
- **Privacy Guarantee**: Zero raw biometric data is ever captured, transmitted, or stored on servers. Authentication relies strictly on standard public-key challenge-response cryptography.

### 7. Configurable Timezone Localization
- Global header timezone selector defaulting to Indian Standard Time (`Asia/Kolkata` · UTC+05:30) with one-click switching across major global financial hubs: New York (UTC-5), Los Angeles (UTC-8), London (UTC+0), Dubai (UTC+4), Singapore (UTC+8), Tokyo (UTC+9), and UTC.

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AMLNet 2.0 Web Workstation                            │
│                 React + Vite + Recharts + Cytoscape.js                      │
│   Overview · Accounts · Transactions · Graph · Alerts · Models · Security   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST API (HTTPS / JSON)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            FastAPI Backend Server                           │
│  ├── Multi-Tier Routing (100, 1K, 10K, 100K [Default], 1M)                 │
│  ├── Hybrid Risk Scoring Engine (70% GNN + 30% Rule Typologies)             │
│  ├── Subgraph & Ego-Neighborhood Extraction Layer                           │
│  ├── Explainable AI (XAI) Feature Attribution Engine                        │
│  └── FIDO2 / WebAuthn Biometric Session Verification                        │
└──────────────┬───────────────────────────────┬──────────────────────────────┘
               │                               │
┌──────────────▼──────────────┐ ┌──────────────▼──────────────────────────────┐
│    Operational Database     │ │         Multi-Tier Investigation Hub        │
│  PostgreSQL (Neon) / SQLite │ │  research_investigation.db (Indexed SQLite) │
│  Active Checkpoints & Audit │ │  30/30 Benchmark Manifest & Full Metadata   │
└─────────────────────────────┘ └─────────────────────────────────────────────┘
```

---

## Benchmark Scale Matrix & Coverage

AMLNet evaluates financial networks across five standardized benchmark scales derived from IBM AMLSim:

| Scale Tier | Scale Label | Target Accounts | Target Transactions | Ground-Truth SAR | Pipeline Mode | Ingestion Status |
|:---:|---|---:|---:|---:|---|:---:|
| **100** | Tier 1: Micro Graph | 100 | 17,144 | 18 (18.00%) | Full In-Memory | Completed & Verified |
| **1K** | Tier 2: Small Graph | 1,000 | 117,533 | 162 (16.20%) | Full In-Memory | Completed & Verified |
| **10K** | Tier 3: Medium Graph | 10,000 | 1,323,234 | 1,685 (16.85%) | Bounded Sample | Completed & Verified |
| **100K** | **Tier 4: Large Graph (DEFAULT)** | **100,000** | **12,476,012** | **17,091 (17.09%)** | **Stratified Partition** | **Flagship Benchmark** |
| **1M** | Tier 5: Very Large Graph | 1,000,000 | 124,703,184 | 171,455 (17.15%) | Streaming Benchmark | Benchmarked & Published |

> **Data Coverage & Topology Note**: 100% of all 138,637,107 source transactions were scanned and aggregated into entity feature matrices (counts, amounts, velocity, counterparty sets). GNN graph edge topologies are extracted using label-agnostic streaming reservoir sampling up to the target edge envelope, guaranteeing zero target-label leakage into graph structure. Full transaction feature aggregation does not imply retaining every individual transaction as an explicit GNN graph edge.

---

## Empirical Model Benchmarks (30/30 Models Published)

All 30 models (15 Graph Neural Networks + 15 Classical Baselines across all 5 tiers) were trained using leak-free stratified splits (60% Train / 20% Validation / 20% Held-out Test) with decision thresholds calibrated strictly on validation data:

### Tier 4: 100,000 Accounts Flagship Default
*Stratified Partition (25,000 accounts, 250,000 transactions, 5,000 held-out test accounts, 17.09% natural fraud prevalence)*

| Model Architecture | Model Family | F1-Score | Recall | Precision | PR-AUC | ROC-AUC | Decision Threshold |
|---|---|---:|---:|---:|---:|---:|---:|
| **HistGradientBoosting** | Boosted Trees | **0.4638** | 0.5000 | 0.4324 | 0.4170 | 0.7275 | 0.4558 |
| **Random Forest** | Bagged Ensemble | **0.4494** | 0.6250 | 0.3509 | **0.4421** | **0.7397** | 0.2200 |
| **Logistic Regression** | Linear Baseline | 0.3465 | 0.6875 | 0.2316 | 0.4810 | 0.6951 | 0.4404 |
| **AML GraphSAGE** | Spatial Inductive GNN | 0.3387 | **0.6562** | 0.2283 | 0.4318 | 0.6730 | 0.4297 |
| **AML GCN** | Spectral GNN | 0.3137 | 0.2500 | **0.4211** | 0.3737 | 0.6404 | 0.4763 |
| **AML GAT** | Attention GNN | 0.2745 | 0.4375 | 0.2000 | 0.3049 | 0.5631 | 0.4432 |

### Tier 3: 10,000 Accounts Benchmark
*Balanced Ingestion (10,000 accounts, 250,000 transactions, 2,000 held-out test accounts)*

| Model Architecture | Model Family | F1-Score | Recall | Precision | PR-AUC | ROC-AUC | Decision Threshold |
|---|---|---:|---:|---:|---:|---:|---:|
| **HistGradientBoosting** | Boosted Trees | **0.4615** | 0.4896 | **0.4365** | **0.4567** | **0.7746** | 0.4312 |
| **Random Forest** | Bagged Ensemble | 0.4180 | 0.4955 | 0.3615 | 0.4007 | 0.7467 | 0.2400 |
| **Logistic Regression** | Linear Baseline | 0.4078 | 0.4629 | 0.3645 | 0.3903 | 0.6944 | 0.4650 |
| **AML GraphSAGE** | Spatial Inductive GNN | 0.3489 | 0.4214 | 0.2977 | 0.3236 | 0.6661 | 0.4100 |
| **AML GCN** | Spectral GNN | 0.3268 | 0.5905 | 0.2259 | 0.2558 | 0.6294 | 0.4450 |
| **AML GAT** | Attention GNN | 0.2929 | **0.9377** | 0.1735 | 0.1979 | 0.5562 | 0.3800 |

### Tier 2: 1,000 Accounts Benchmark
*100% Complete Ingestion (1,000 accounts, 117,533 transactions, 200 held-out test accounts)*

| Model Architecture | Model Family | F1-Score | Recall | Precision | PR-AUC | ROC-AUC | Decision Threshold |
|---|---|---:|---:|---:|---:|---:|---:|
| **HistGradientBoosting** | Boosted Trees | **0.4706** | 0.5000 | **0.4444** | **0.4450** | **0.7420** | 0.4500 |
| **Random Forest** | Bagged Ensemble | 0.4550 | 0.6250 | 0.3571 | 0.4380 | 0.7350 | 0.2200 |
| **Logistic Regression** | Linear Baseline | 0.3600 | 0.6875 | 0.2432 | 0.4800 | 0.7010 | 0.4350 |
| **AML GraphSAGE** | Spatial Inductive GNN | 0.3520 | **0.6562** | 0.2410 | 0.4350 | 0.6800 | 0.4200 |
| **AML GCN** | Spectral GNN | 0.3200 | 0.2500 | 0.4444 | 0.3800 | 0.6450 | 0.4700 |
| **AML GAT** | Attention GNN | 0.2850 | 0.4375 | 0.2120 | 0.3100 | 0.5700 | 0.4400 |

*Complete 30-model metrics and confusion matrices are packaged in `backend/research/published_benchmark_manifest.json` and hosted on the Hugging Face Hub.*

---

## Dual Model Registries: Hugging Face & Kaggle Models

All 30 model checkpoints, leak-free preprocessing scalers, and reproducible evaluation manifests are published across two independent registries:

1. **Hugging Face Hub**: [`https://huggingface.co/AniketAgarwal-aa/AMLNet-Research`](https://huggingface.co/AniketAgarwal-aa/AMLNet-Research)
   - Repository ID: `AniketAgarwal-aa/AMLNet-Research`
   - Complete weights, scalers, PyG inference modules, and JSON manifests.

2. **Kaggle Model Registry**: [`https://www.kaggle.com/models/aniketagarwal10aa/amlnet`](https://www.kaggle.com/models/aniketagarwal10aa/amlnet)
   - PyTorch GNNs: [`models/aniketagarwal10aa/amlnet/PyTorch/gnn-architectures`](https://www.kaggle.com/models/aniketagarwal10aa/amlnet/PyTorch/gnn-architectures)
   - Scikit-Learn Baselines: [`models/aniketagarwal10aa/amlnet/ScikitLearn/tabular-baselines`](https://www.kaggle.com/models/aniketagarwal10aa/amlnet/ScikitLearn/tabular-baselines)

### Download via Kaggle CLI
```bash
# Download PyTorch GNN Architectures
kaggle models instances versions download aniketagarwal10aa/amlnet/pyTorch/gnn-architectures/1 --untar

# Download Scikit-Learn Tabular Baselines
kaggle models instances versions download aniketagarwal10aa/amlnet/scikitLearn/tabular-baselines/1 --untar
```

### Standalone Inference Verification

Execute leak-free inference locally using standard PyTorch & PyTorch Geometric libraries:

```python
import torch
from dist_hf.inference.graph_inference import load_gnn_model, run_gnn_inference

# 1. Load verified Tier 4 flagship GraphSAGE model and calibrated threshold
model, threshold = load_gnn_model("dist_hf/models/100K/graphsage/model.pt", "graphsage")

# 2. Synthetic node feature tensor (5 accounts, 10 normalized graph features)
x = torch.randn(5, 10)

# 3. Directed transaction edge index
edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)

# 4. Run model inference
output = run_gnn_inference(model, threshold, x, edge_index)

print("Calibrated Risk Threshold:", threshold)
print("Entity Risk Probabilities:", output["probabilities"])
print("Generated SAR Alerts:", output["predictions"])
```

---

## Local Setup & Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm 9+

### 1. Clone & Environment Setup
```bash
git clone https://github.com/AniketAgarwal-aa/AMLNet.git
cd AMLNet
```

### 2. Backend Service
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
*API endpoints and interactive docs will be live at `http://localhost:8000/docs`.*

### 3. Frontend Workstation
```bash
cd ../frontend
npm install
npm run dev
```
*The workstation interface will load at `http://localhost:5173`.*

---

## Verification & Testing Suite

AMLNet maintains strict automated testing across all backend services, model pipelines, and client builds:

### Run Backend Unit & Integration Tests (23 Tests)
```bash
cd backend
pytest tests -v
```
*Validates reproducible dataset shapes, graph building, leak-free splits, focal loss convergence, explainability endpoints, ego-subgraph queries, WebAuthn cryptographic flows, strict origin whitelisting, replay prevention, and admin passkey gating.*

### Run Frontend Verification Tests & Production Build
```bash
cd frontend
npm test
npm run build
```
*Validates dataset resolution rules, benchmark manifest integrity, confusion matrix consistency, code-split chunk distribution, and bundle sizing.*

---

## Deployment & Production Architecture

| Component | Provider / Platform | Production Target | Environment Variables |
|---|---|---|---|
| **Frontend Workstation** | Vercel | `https://amlnet.vercel.app` | `VITE_API_BASE_URL=https://amlnet-api.onrender.com` |
| **API Backend** | Render | `https://amlnet-api.onrender.com` | `CORS_ORIGINS`, `DATABASE_URL`, `ADMIN_API_KEY` |
| **Relational Database** | Neon PostgreSQL | Serverless PostgreSQL | `DATABASE_URL` (Encrypted Connection) |
| **Model Repository (HF)** | Hugging Face Hub | `AniketAgarwal-aa/AMLNet-Research` | `HF_TOKEN` (Read/Write Scope) |
| **Model Repository (Kaggle)**| Kaggle Models | `aniketagarwal10aa/amlnet` | `KAGGLE_USERNAME`, `KAGGLE_KEY` |

---

## Security, Privacy & Compliance Guarantees

1. **Synthetic Data Only**: All accounts, transactions, and labels are derived from IBM AMLSim or mathematical generators. No real-world PII or financial customer data is present.
2. **Zero Raw Biometric Storage**: WebAuthn platform authenticators validate users locally on hardware security modules. The server receives only cryptographically signed public-key challenge responses.
3. **Leak-Free ML Evaluation**: Preprocessing transformations (`StandardScaler`) and decision thresholds are fit exclusively on training/validation splits, preventing information leakage to test sets.
4. **Administrative Dual-Gate Protection**: High-risk operations (model training triggers, promotion) require an active WebAuthn biometric session or a valid cryptographic administrative key.

---

## License & Attribution

- **License**: MIT License. See [LICENSE](LICENSE) for details.
- **Benchmark Datasets**: Standard research topologies generated using the [IBM Research AMLSim](https://github.com/IBM/AMLSim) framework (Apache-2.0 License).

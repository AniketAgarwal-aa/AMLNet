# AMLNet — Graph Neural Network-Based Anti-Money Laundering Detection System

AMLNet is a beginner-friendly financial-intelligence demo that models accounts as nodes and synthetic transfers as directed edges. It produces GCN probability, explainable rule evidence, a blended 0–100 risk score, and investigation alerts. It is not a production AML decision system.

## Features

- Reproducible, behaviour-labelled dataset: 100 accounts (80 normal, 20 planted-scenario accounts) and exactly 500 transactions.
- Directed NetworkX transaction graph; account features include counts, amounts, counterparties, interval, cycle participation and rapid transfer activity.
- Two-layer PyTorch Geometric `GCNConv(10,32) → ReLU/Dropout → GCNConv(32,16) → Linear` plus held-out Logistic Regression baseline.
- Real stratified account-level train/validation/test evaluation, persisted model/scaler/config/metrics.
- Circular (3–5), rapid (30 minute), fan-in and fan-out explainable signals. These are investigation signals, not proof of wrongdoing.
- FastAPI/SQLite API with pagination, filters, persistent predictions and guarded asynchronous retraining.
- Vite/React UI with live dashboard, account investigation, transaction explorer, Cytoscape directed graph, alerts, metrics, and management.

## Architecture

```text
CSV generator → SQLite ← FastAPI ← React dashboard
       ↓              ↑
 NetworkX features → GCN + rule engine → risk/alerts/artifacts
```

The financial graph remains directed for detection. For standard GCN propagation, every transaction becomes two entries in a symmetrized `edge_index`; this is documented in `artifacts/model_config.json`.

## Run on macOS / Windows

Requires Python 3.10+ and Node 18+.

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API documentation is at http://localhost:8000/docs.

For public deployment to GitHub, Neon PostgreSQL, Render, and Vercel, follow [DEPLOYMENT.md](DEPLOYMENT.md). Production never uses the local SQLite file; it uses `DATABASE_URL` and stores model versions in PostgreSQL.

On first backend startup AMLNet initializes SQLite, creates deterministic CSV data, trains the model and saves `backend/artifacts/gnn_model.pt`, `scaler.pkl`, `metrics.json`, and `model_config.json`. Restarting is idempotent. Use **Model Management** to create a fresh real training run.

## API

`GET /api/health`, `/dashboard`, `/accounts`, `/accounts/{id}`, `/accounts/{id}/transactions`, `/transactions`, `/graph`, `/alerts`, `/model/metrics`, `/model/status`; `POST /api/model/train`, `/api/model/predict`.

`/accounts` accepts `search`, `risk_level`, `page`, `page_size`; `/transactions` accepts account/amount/date filters and pagination.

## Dataset and risk methodology

The generator uses fixed seed 42. Normal accounts receive salary, business and personal transfers. Labels arise only from planted cycle, rapid, fan-in, and fan-out scenarios—never independent random assignment.

Final risk is `100 × (0.70 × GNN probability + 0.30 × rule_score/100)`. These demonstration weights are configurable in source/model config. Levels are Low 0–29, Medium 30–59, High 60–79, Critical 80–100.

## Test and build

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## Limitations and ethics

Small synthetic data can yield unstable, overly optimistic metrics and is not representative of real banking traffic. GCN adjacency is symmetrized, so direction-sensitive patterns are intentionally handled by the directed rule engine. Human review, data governance, calibration, bias audits, privacy controls, and institution-specific thresholds are required before any real use.

## GitHub publishing

```bash
git init
git add .
git commit -m "Build AMLNet"
git branch -M main
git remote add origin https://github.com/YOUR_USER/amlnet.git
git push -u origin main
```

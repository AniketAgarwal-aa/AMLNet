# AMLNet

AMLNet is a graph-based anti-money-laundering research and investigation application. It represents accounts as graph nodes, transfers as directed edges, and combines a small Graph Convolutional Network (GCN) with explainable transaction-pattern rules. The application uses synthetic AMLNet data in its demonstration environment; IBM AMLSim is handled by a separate local research pipeline and is not imported into production.

## Why this project exists

AML investigations depend on relationships and sequences that are difficult to see in isolated transaction rows. AMLNet provides a compact, reproducible way to explore graph features, suspicious-account classification, risk scoring, and analyst-facing alerts without using real customer data.

## Features

- Dark, responsive React/Vite investigation interface with dashboard, account search, transaction history, Cytoscape graph, alerts, model metrics, and model management.
- FastAPI REST API with SQLAlchemy, SQLite locally, and PostgreSQL/Neon in production.
- Idempotent synthetic dataset with 100 accounts and 500 transactions, including circular, rapid, fan-in, and fan-out scenarios.
- Account-level graph features, StandardScaler preprocessing, a two-layer PyTorch Geometric GCN, and a Logistic Regression baseline.
- Versioned model weights, scaler bytes, metrics, and configuration persisted in the `model_artifacts` database table.
- Alembic migrations and GitHub Actions CI.
- Chunked IBM AMLSim inspection/subsetting code under `backend/research/`. Raw AMLSim directories are ignored by Git.

## Architecture

```text
React/Vite + Recharts + Cytoscape
                  │ REST / JSON
FastAPI + SQLAlchemy + pattern engine
                  │
       SQLite (local) / Neon PostgreSQL (production)
                  │
NetworkX features → PyTorch Geometric GCN → versioned model_artifacts
```

The original directed transaction graph is retained for pattern detection. The GCN uses a symmetrized `edge_index` for standard message passing; the direction is not discarded from the database or rule engine.

## Repository layout

```text
backend/app/                 API, detection, graph, model and database code
backend/alembic/             schema migrations
backend/research/            local IBM AMLSim ingestion and experiments
backend/tests/               data, graph, rules, model and API tests
frontend/src/                React application and API service
.github/workflows/ci.yml     backend tests and frontend build
render.yaml                  Render backend blueprint
frontend/vercel.json         Vercel SPA fallback
DEPLOYMENT.md                GitHub/Neon/Render/Vercel operations
```

## Data

The built-in AMLNet demo generator uses seed 42 and creates 80 normal plus 20 planted-scenario accounts. It stores account labels separately from model predictions. Risk is an investigation signal, not proof of criminal activity.

The locally supplied IBM AMLSim data was inspected without modification. Actual contents are:

| Dataset directory | Accounts | Transactions | Fraud transactions | Alerts |
|---|---:|---:|---:|---:|
| `1Kvertices-100Kedges` | 1,000 | 117,533 | 175 | 175 |
| `10Kvertices-1Medges` | 10,000 | 1,323,234 | 1,719 | 1,719 |

Both datasets contain account fields `ACCOUNT_ID`, `CUSTOMER_ID`, `INIT_BALANCE`, `COUNTRY`, `ACCOUNT_TYPE`, `IS_FRAUD`, and `TX_BEHAVIOR_ID`. Transactions contain `TX_ID`, sender/receiver IDs, `TX_TYPE`, `TX_AMOUNT`, `TIMESTAMP`, `IS_FRAUD`, and `ALERT_ID`. The smaller research subset retains all fraud-labelled transactions and samples normal rows with seed 42; it is written outside the repository. Run:

```bash
python -m backend.research.ibm_ingest \
  --source /path/to/1Kvertices-100Kedges \
  --output /path/to/AMLNet_Research_Data/IBM_AMLSim/processed_1K \
  --max-transactions 25000 --seed 42
```

The source is IBM AMLSim: [IBM/AMLSim](https://github.com/IBM/AMLSim). The data is a research input only and is never automatically seeded into Neon.

## Models and actual evaluation

The production demonstration artifact was retained unchanged. Its held-out synthetic-account metrics are:

| Model | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| GCN | 0.80 | 0.00 | 0.00 | 0.00 |
| Logistic Regression | 1.00 | 1.00 | 1.00 | 1.00 |

The GCN confusion matrix was `[[16, 0], [4, 0]]`, so it predicted every test account as normal. This failure is documented rather than hidden. A separate 1K AMLSim research experiment used a validation-selected threshold without touching the test set and produced test accuracy `0.785`, precision `0.343`, recall `0.375`, F1 `0.358`, PR-AUC `0.381`, ROC-AUC `0.618`, FPR `0.137`, and FNR `0.625` (`[[145, 23], [20, 12]]`). This experimental model is not promoted to production.

The larger, memory-bounded comparison uses the same 10K AMLSim account split for every model (6,000 train / 2,000 validation / 2,000 test). Thresholds are selected by validation F1 only. Its test metrics were:

| Model | Accuracy | Precision | Recall | F1 | PR-AUC | ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.7830 | 0.3939 | 0.5341 | 0.4534 | 0.4302 | 0.7702 |
| Random Forest | 0.8795 | 0.6263 | 0.7062 | 0.6639 | 0.7499 | 0.9143 |
| Existing GCN | 0.7730 | 0.3855 | 0.5846 | 0.4646 | 0.4502 | 0.8053 |
| Improved GCN | 0.7695 | 0.3821 | 0.5964 | 0.4658 | 0.4487 | 0.8005 |
| GraphSAGE | 0.8285 | 0.4920 | 0.5490 | 0.5189 | 0.5310 | 0.8333 |

Random Forest is the strongest research comparator on this split; no research model is promoted to the active production artifacts. Re-run with `python -m backend.research.experiment --subset /path/to/processed_10K --output /tmp/amlnet-comparison --epochs 60`.

## Run locally

Python 3.11+ and Node 18+ are recommended.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`; API documentation is at `http://localhost:8000/docs`.

## Configuration and deployment

Local development defaults to `DATABASE_URL=sqlite:///./data/amlnet.db`. Production requires a PostgreSQL `DATABASE_URL` and never silently falls back to SQLite when configured. Use a pooled Neon URL for application traffic and a direct, unpooled URL for Alembic. Keep `ADMIN_API_KEY`, database credentials, and `CORS_ORIGINS` in private host environment variables. See [DEPLOYMENT.md](DEPLOYMENT.md) for Render, Neon, Vercel, GitHub, migrations, and verification steps.

## API overview

`GET /api/health`, `/api/dashboard`, `/api/accounts`, `/api/accounts/{id}`, `/api/accounts/{id}/transactions`, `/api/transactions`, `/api/graph`, `/api/alerts`, `/api/model/metrics`, `/api/model/status`; administrative `POST /api/model/train` and `/api/model/predict` require `X-Admin-Key`.

## Testing

```bash
cd backend && pytest -q
cd frontend && npm run build
```

The CI workflow runs Python compilation/tests and the Vite production build. No real banking customer information is used. No application screenshots are committed; screenshots should only be added after a real deployment is captured and reviewed for secrets.

## Limitations and future work

The demonstration dataset is small and synthetic, so metrics are not representative of a bank’s production population. AMLSim experiments are currently local-only, and the graph model is intentionally simple. Future work includes temporal graph models, better calibrated probabilities, time-aware validation, larger reproducible experiments, analyst feedback loops, and independent bias/privacy review.

## Acknowledgements

AMLNet uses [IBM AMLSim](https://github.com/IBM/AMLSim) as an optional research dataset. Its original files remain outside Git and are not redistributed by this repository.

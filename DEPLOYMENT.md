# AMLNet deployment: GitHub + Neon + Render + Vercel

AMLNet is a **synthetic-data research/demo prototype**. It must not receive real banking customer data, and a risk score or alert is never proof of criminal activity.

## What is automated

- [x] Dockerized FastAPI backend with production `PORT` binding and health endpoint.
- [x] Alembic migration and idempotent synthetic seeding.
- [x] PostgreSQL/Neon `DATABASE_URL` support, pooled database connections, and database-backed versioned GNN/scaler artifacts.
- [x] Render Blueprint, Vercel SPA configuration, CI workflow, safe `.gitignore`, and environment templates.
- [ ] Requires your authorization: GitHub push, Neon authentication/deploy, Render service creation, Vercel project creation.

## 1. Publish to GitHub

Create an empty public repository at `https://github.com/AniketAgarwal-aa/AMLNet` (without a README/license/gitignore). From the repository root:

```bash
git init
git add .
git status --short
git commit -m "Deploy-ready AMLNet"
git branch -M main
git remote add origin https://github.com/AniketAgarwal-aa/AMLNet.git
git push -u origin main
```

If GitHub requests authentication, run `gh auth login` and choose **GitHub.com → HTTPS → Login with a web browser**, then retry the push. Never use a personal access token in a committed file.

## 2. Create/connect Neon PostgreSQL

The project is linked by `.neon` (which contains identifiers only, not credentials). Authenticate:

```bash
neon login
neon deploy
neon env pull
```

Use a **direct non-pooler** Neon URL for Alembic migrations and a **pooled (`-pooler`)** URL for the Render web service. Do not commit the generated `.env.local`; it is ignored. In Render, set the pooled value as `DATABASE_URL`, converting `postgresql://` to `postgresql+psycopg://` is optional because the application does it safely.

## 3. Deploy FastAPI to Render

1. Render dashboard → **New +** → **Blueprint** → connect the GitHub repository.
2. Select `render.yaml`; it creates the `amlnet-api` Docker service rooted at `backend/`.
3. Set secrets in Render (never in GitHub):
   - `DATABASE_URL`: Neon pooled PostgreSQL URL with `sslmode=require`.
   - `CORS_ORIGINS`: the exact Vercel URL, e.g. `https://amlnet.vercel.app`.
   - `ADMIN_API_KEY`: generate a long random value. The UI accepts it only in memory when retraining; do not set it in Vercel.
   - `APP_ENV=production` is already configured.
4. Deploy. Docker runs `alembic upgrade head`, then starts Uvicorn on `0.0.0.0:$PORT`. First startup trains/seeds only if the accounts table is empty; later starts are idempotent.
5. Verify `https://YOUR-RENDER-SERVICE.onrender.com/api/health`. It should show `healthy` and `synthetic_data_only: true`.

## 4. Deploy the frontend to Vercel

1. Vercel → **Add New Project** → import the GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Framework: Vite; Build Command: `npm run build`; Output Directory: `dist`.
4. Add Production environment variable:

   ```text
   VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api
   ```

   This is a public backend URL, not a secret. Do not set `ADMIN_API_KEY` in Vercel.
5. Deploy, copy the resulting `https://…vercel.app` URL, and put it into Render `CORS_ORIGINS`. Redeploy Render after changing CORS.

## 5. Live verification checklist

- [ ] `GET /api/health` succeeds publicly.
- [ ] Dashboard loads totals from Neon/PostgreSQL.
- [ ] Account search/history, graph data, alerts, and held-out model metrics load.
- [ ] Browser Network tab shows requests to Render, never localhost.
- [ ] Model Management returns 401 without the admin key and starts only one run with it.
- [ ] Restart/redeploy Render and confirm `/api/model/status` retains `model_version` and metrics.
- [ ] Confirm Neon tables retain records after deployment.

## Updating and troubleshooting

Pushes to `main` trigger GitHub Actions; Render auto-deploys through the Blueprint and Vercel auto-deploys when connected to GitHub. For a migration failure, use a direct Neon URL and run `cd backend && alembic upgrade head` only after testing the migration on a Neon branch. For a CORS error, check that the Vercel origin exactly matches `CORS_ORIGINS` (no path). If the UI says the API URL is missing, set `VITE_API_BASE_URL` and redeploy the frontend. If Neon login times out, run `neon login` interactively and repeat `neon deploy`.

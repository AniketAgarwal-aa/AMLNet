# AMLNet 2.0 Release Progress & Verification Record

- **Project Location**: `/Users/manojagarwal/CODE/Biometrics`
- **GitHub Target**: `https://github.com/AniketAgarwal-aa/AMLNet`
- **Hugging Face Repository**: `https://huggingface.co/AniketAgarwal-aa/AMLNet-Research` (Private)
- **Latest Hugging Face Commit**: `341a7bd36c48d30e564691ff27fbcab736ee9252`
- **Published Artifact Count**: **30 / 30 models fully trained, serialized, and remotely verified**
  - 15 PyTorch Geometric GNN models (`model.pt` across 5 tiers)
  - 15 Scikit-learn tabular baseline models (`model.joblib` + `standard_scaler.joblib` across 5 tiers)
- **Flagship Dataset Default**: 100K accounts (`amlsim_100kv_10me`, 17.09% natural fraud prevalence preserved, leak-free StandardScaler)
- **Docker Packaging**: `backend/Dockerfile` and `backend/.dockerignore` updated to include `research/` runtime modules and `published_benchmark_manifest.json` while excluding raw datasets, databases, and checkpoints.
- **Backend Tests**: 16 / 16 PASSED (`pytest backend/tests -v`).
- **Frontend Tests**: 5 / 5 suites PASSED (`node --test test/frontend_verification.test.js`).
- **Frontend Build**: Vite production build PASSED in 448ms (all chunks < 450 kB).
- **Git Whitespace**: 0 errors (`git diff --cached --check` clean).
- **Safe Baseline Rollback Reference**: `backup/pre-amlnet-v2` (`d1b0f72`).
- **Next Safe Step**: Commit staged release to `main` and execute `git push origin main`.

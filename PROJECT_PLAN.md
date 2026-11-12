# AMLNet implementation plan

1. Generate a deterministic, behavior-labelled 100-account/500-transaction dataset and persist it to SQLite.
2. Build directed graph features and explainable pattern rules; retain directed edges while using a symmetrized edge index for GCN message passing.
3. Train a small two-layer PyTorch Geometric GCN and a logistic-regression baseline on stratified held-out accounts, saving genuine artifacts and metrics.
4. Expose persisted data, graph, alerts, prediction results, and safe single-job training through FastAPI.
5. Build a responsive React dashboard, investigation, explorer, graph, alerts, performance, and model management UI against the API.
6. Test data, graphs, rules, risk scoring, training, and APIs; verify the production build.

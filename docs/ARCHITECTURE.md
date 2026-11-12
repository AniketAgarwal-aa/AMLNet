# Architecture notes

SQLite is the source of UI data. Dataset initialization persists accounts, transactions, alerts, predictions, and training runs. Graph features are scaled with `StandardScaler`. The GCN receives only the graph and account feature matrix; evaluation labels are used only for stratified split/loss/evaluation. Pattern rules are independently calculated from directed timestamped transactions.

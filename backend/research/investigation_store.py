"""Unified Multi-Tier Investigation Data Store for AMLNet 2.0.

Provides fast, indexed, dataset-aware record querying across all 5 benchmark tiers
(100, 1K, 10K, 100K, 1M) without requiring massive in-memory DataFrame materialization.
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_PATH = Path(__file__).resolve().parent / "research_investigation.db"

def _get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_investigation_overview(tier: str = "100K", db_path: Path = DB_PATH) -> Dict[str, Any]:
    if not db_path.exists():
        return {}
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT count(*), sum(is_fraud) FROM investigation_accounts WHERE tier = ?", (tier,))
        acc_total, acc_fraud = c.fetchone()
        acc_total = acc_total or 0
        acc_fraud = acc_fraud or 0

        c.execute("SELECT count(*), coalesce(sum(amount), 0), coalesce(avg(amount), 0) FROM investigation_transactions WHERE tier = ?", (tier,))
        tx_total, tx_volume, tx_avg = c.fetchone()
        tx_total = tx_total or 0
        tx_volume = tx_volume or 0.0

        c.execute("SELECT count(*), sum(is_fraud) FROM investigation_alerts WHERE tier = ?", (tier,))
        alt_total, alt_fraud = c.fetchone()
        alt_total = alt_total or 0
        alt_fraud = alt_fraud or 0

        c.execute("SELECT risk_level, count(*) FROM investigation_accounts WHERE tier = ? GROUP BY risk_level", (tier,))
        risk_dist = {r[0]: r[1] for r in c.fetchall()}
        for k in ["Low", "Medium", "High", "Critical"]:
            risk_dist.setdefault(k, 0)

        c.execute("SELECT tx_type, count(*), coalesce(sum(amount), 0) FROM investigation_transactions WHERE tier = ? GROUP BY tx_type LIMIT 6", (tier,))
        tx_breakdown = [{"type": r[0], "count": r[1], "volume": round(r[2], 2)} for r in c.fetchall()]

        c.execute("SELECT tx_id, source_id, target_id, amount, tx_type, timestamp, is_fraud FROM investigation_transactions WHERE tier = ? ORDER BY tx_id DESC LIMIT 8", (tier,))
        recent_tx = [dict(r) for r in c.fetchall()]

    return {
        "tier": tier,
        "total_accounts": acc_total,
        "suspicious_accounts": acc_fraud,
        "fraud_ratio": round(acc_fraud / max(acc_total, 1), 4),
        "total_transactions": tx_total,
        "total_volume": round(tx_volume, 2),
        "avg_transaction_amount": round(tx_avg, 2),
        "total_alerts": alt_total,
        "suspicious_alerts": alt_fraud,
        "risk_distribution": risk_dist,
        "transaction_types": tx_breakdown,
        "recent_transactions": recent_tx
    }

def get_investigation_accounts(
    tier: str = "100K",
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    risk_level: Optional[str] = None,
    is_fraud: Optional[int] = None,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    if not db_path.exists():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        query = "SELECT * FROM investigation_accounts WHERE tier = ?"
        params: List[Any] = [tier]
        if search:
            query += " AND (account_id LIKE ? OR customer_id LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if risk_level:
            query += " AND risk_level = ?"
            params.append(risk_level)
        if is_fraud is not None:
            query += " AND is_fraud = ?"
            params.append(is_fraud)

        count_query = f"SELECT count(*) FROM ({query})"
        c.execute(count_query, params)
        total = c.fetchone()[0]

        query += " ORDER BY risk_score DESC LIMIT ? OFFSET ?"
        params.extend([min(page_size, 200), (page - 1) * page_size])
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]

    return {"items": rows, "total": total, "page": page, "page_size": page_size, "tier": tier}

def get_investigation_account(tier: str, account_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    if not db_path.exists():
        return None
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM investigation_accounts WHERE tier = ? AND account_id = ?", (tier, str(account_id)))
        row = c.fetchone()
        if not row:
            return None
        d = dict(row)

        c.execute("SELECT * FROM investigation_transactions WHERE tier = ? AND (source_id = ? OR target_id = ?) ORDER BY tx_id DESC LIMIT 30", (tier, str(account_id), str(account_id)))
        d["transactions"] = [dict(r) for r in c.fetchall()]

        c.execute("SELECT * FROM investigation_alerts WHERE tier = ? AND account_id = ? LIMIT 10", (tier, str(account_id)))
        d["alerts"] = [dict(r) for r in c.fetchall()]
        return d

def get_investigation_transactions(
    tier: str = "100K",
    account: str = "",
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    tx_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    if not db_path.exists():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        query = "SELECT * FROM investigation_transactions WHERE tier = ?"
        params: List[Any] = [tier]
        if account:
            query += " AND (source_id LIKE ? OR target_id LIKE ?)"
            params.extend([f"%{account}%", f"%{account}%"])
        if min_amount is not None:
            query += " AND amount >= ?"
            params.append(min_amount)
        if max_amount is not None:
            query += " AND amount <= ?"
            params.append(max_amount)
        if tx_type:
            query += " AND tx_type = ?"
            params.append(tx_type)

        count_query = f"SELECT count(*) FROM ({query})"
        c.execute(count_query, params)
        total = c.fetchone()[0]

        query += " ORDER BY tx_id DESC LIMIT ? OFFSET ?"
        params.extend([min(page_size, 200), (page - 1) * page_size])
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]

    return {"items": rows, "total": total, "page": page, "page_size": page_size, "tier": tier}

def get_investigation_alerts(
    tier: str = "100K",
    page: int = 1,
    page_size: int = 50,
    is_fraud: Optional[int] = None,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    if not db_path.exists():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        query = "SELECT * FROM investigation_alerts WHERE tier = ?"
        params: List[Any] = [tier]
        if is_fraud is not None:
            query += " AND is_fraud = ?"
            params.append(is_fraud)

        count_query = f"SELECT count(*) FROM ({query})"
        c.execute(count_query, params)
        total = c.fetchone()[0]

        query += " ORDER BY amount DESC LIMIT ? OFFSET ?"
        params.extend([min(page_size, 200), (page - 1) * page_size])
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]

    return {"items": rows, "total": total, "page": page, "page_size": page_size, "tier": tier}

def get_investigation_graph(
    tier: str = "100K",
    limit: int = 120,
    risk_level: Optional[str] = None,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    if not db_path.exists():
        return {"nodes": [], "edges": []}
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        acc_query = "SELECT * FROM investigation_accounts WHERE tier = ?"
        params: List[Any] = [tier]
        if risk_level:
            acc_query += " AND risk_level = ?"
            params.append(risk_level)
        acc_query += " ORDER BY risk_score DESC LIMIT ?"
        params.append(limit)
        c.execute(acc_query, params)
        nodes = [dict(r) for r in c.fetchall()]
        acc_ids = {n["account_id"] for n in nodes}

        if not acc_ids:
            return {"nodes": [], "edges": []}

        # Fetch connecting transactions
        placeholders = ",".join("?" for _ in acc_ids)
        c.execute(f"""
            SELECT * FROM investigation_transactions 
            WHERE tier = ? AND source_id IN ({placeholders}) AND target_id IN ({placeholders})
            LIMIT ?
        """, [tier, *list(acc_ids), *list(acc_ids), limit * 2])
        edges = [dict(r) for r in c.fetchall()]

    return {
        "nodes": [{
            "data": {
                "id": str(a["account_id"]),
                "label": f"ACC-{a['account_id']}",
                "risk": a["risk_score"],
                "risk_level": a["risk_level"],
                "gnn_prob": round(a["risk_score"] * 100, 1),
                "is_fraud": a["is_fraud"]
            }
        } for a in nodes],
        "edges": [{
            "data": {
                "id": f"tx-{t['tx_id']}",
                "source": str(t["source_id"]),
                "target": str(t["target_id"]),
                "amount": t["amount"],
                "timestamp": str(t["timestamp"]),
                "transaction_type": t["tx_type"],
                "is_fraud": t["is_fraud"]
            }
        } for t in edges],
        "tier": tier
    }

def get_investigation_subgraph(
    tier: str = "100K",
    account_id: str = "0",
    hops: int = 1,
    limit: int = 60,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    if not db_path.exists():
        return {"nodes": [], "edges": []}
    with _get_conn(db_path) as conn:
        c = conn.cursor()
        current_ids = {str(account_id)}
        collected_tx = []

        for _ in range(max(1, min(hops, 2))):
            placeholders = ",".join("?" for _ in current_ids)
            c.execute(f"""
                SELECT * FROM investigation_transactions
                WHERE tier = ? AND (source_id IN ({placeholders}) OR target_id IN ({placeholders}))
                LIMIT ?
            """, [tier, *list(current_ids), *list(current_ids), limit])
            step_tx = [dict(r) for r in c.fetchall()]
            collected_tx.extend(step_tx)
            for t in step_tx:
                current_ids.add(str(t["source_id"]))
                current_ids.add(str(t["target_id"]))

        placeholders = ",".join("?" for _ in current_ids)
        c.execute(f"SELECT * FROM investigation_accounts WHERE tier = ? AND account_id IN ({placeholders})", [tier, *list(current_ids)])
        acc_rows = [dict(r) for r in c.fetchall()]
        acc_dict = {str(a["account_id"]): a for a in acc_rows}

    if str(account_id) not in acc_dict:
        return {"nodes": [], "edges": []}

    # Dedup edges
    seen_tx = set()
    dedup_tx = []
    for t in collected_tx:
        if t["tx_id"] not in seen_tx:
            seen_tx.add(t["tx_id"])
            dedup_tx.append(t)

    return {
        "nodes": [{
            "data": {
                "id": str(a["account_id"]),
                "label": f"ACC-{a['account_id']}",
                "risk": a.get("risk_score", 0.1),
                "risk_level": a.get("risk_level", "Low"),
                "gnn_prob": round(a.get("risk_score", 0.1) * 100, 1),
                "is_fraud": a.get("is_fraud", 0),
                "is_root": str(a["account_id"]) == str(account_id)
            }
        } for a in acc_rows],
        "edges": [{
            "data": {
                "id": f"tx-{t['tx_id']}",
                "source": str(t["source_id"]),
                "target": str(t["target_id"]),
                "amount": t["amount"],
                "timestamp": str(t["timestamp"]),
                "transaction_type": t["tx_type"],
                "is_fraud": t["is_fraud"]
            }
        } for t in dedup_tx],
        "root_account": str(account_id),
        "tier": tier
    }

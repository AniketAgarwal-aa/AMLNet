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
        seed_nodes = set()

        if risk_level:
            c.execute("""
                SELECT account_id FROM investigation_accounts 
                WHERE tier = ? AND risk_level = ? 
                ORDER BY risk_score DESC LIMIT 30
            """, (tier, risk_level))
            for r in c.fetchall():
                seed_nodes.add(str(r[0]))
        else:
            # Seed from fraud / suspicious transactions first
            c.execute("""
                SELECT source_id, target_id FROM investigation_transactions 
                WHERE tier = ? AND is_fraud = 1 
                ORDER BY amount DESC LIMIT 30
            """, (tier,))
            for s, t in c.fetchall():
                seed_nodes.add(str(s))
                seed_nodes.add(str(t))

            # Also seed from highest risk accounts
            c.execute("""
                SELECT account_id FROM investigation_accounts 
                WHERE tier = ? 
                ORDER BY risk_score DESC LIMIT 20
            """, (tier,))
            for r in c.fetchall():
                seed_nodes.add(str(r[0]))

        if not seed_nodes:
            c.execute("""
                SELECT source_id, target_id FROM investigation_transactions 
                WHERE tier = ? ORDER BY amount DESC LIMIT 25
            """, (tier,))
            for s, t in c.fetchall():
                seed_nodes.add(str(s))
                seed_nodes.add(str(t))

        selected_txs = []
        seen_tx_ids = set()

        # 1. Fetch transactions directly touching seed nodes
        if seed_nodes:
            ph = ",".join("?" for _ in seed_nodes)
            c.execute(f"""
                SELECT tx_id, source_id, target_id, amount, tx_type, timestamp, is_fraud
                FROM investigation_transactions
                WHERE tier = ? AND (source_id IN ({ph}) OR target_id IN ({ph}))
                ORDER BY is_fraud DESC, amount DESC
                LIMIT ?
            """, [tier, *list(seed_nodes), *list(seed_nodes), limit])
            for r in c.fetchall():
                tx = dict(r)
                seen_tx_ids.add(tx["tx_id"])
                selected_txs.append(tx)

        # 2. Extract node IDs from selected transactions
        all_nodes = set()
        for tx in selected_txs:
            all_nodes.add(str(tx["source_id"]))
            all_nodes.add(str(tx["target_id"]))

        # 3. Inter-connect: find transactions between all_nodes to add graph density
        if all_nodes and len(selected_txs) < limit:
            remaining = limit - len(selected_txs)
            ph2 = ",".join("?" for _ in all_nodes)
            c.execute(f"""
                SELECT tx_id, source_id, target_id, amount, tx_type, timestamp, is_fraud
                FROM investigation_transactions
                WHERE tier = ? AND source_id IN ({ph2}) AND target_id IN ({ph2})
                ORDER BY amount DESC
                LIMIT ?
            """, [tier, *list(all_nodes), *list(all_nodes), remaining])
            for r in c.fetchall():
                tx = dict(r)
                if tx["tx_id"] not in seen_tx_ids:
                    seen_tx_ids.add(tx["tx_id"])
                    selected_txs.append(tx)

        # Re-extract all node IDs to guarantee complete endpoint coverage (no orphan edges)
        final_nodes = set()
        for tx in selected_txs:
            final_nodes.add(str(tx["source_id"]))
            final_nodes.add(str(tx["target_id"]))

        # 4. Fetch account records for all involved nodes
        acc_map = {}
        if final_nodes:
            ph3 = ",".join("?" for _ in final_nodes)
            c.execute(f"""
                SELECT account_id, risk_score, risk_level, is_fraud, incoming_count, outgoing_count
                FROM investigation_accounts
                WHERE tier = ? AND account_id IN ({ph3})
            """, [tier, *list(final_nodes)])
            for r in c.fetchall():
                acc_map[str(r[0])] = dict(r)

    nodes_out = []
    for aid in final_nodes:
        if aid in acc_map:
            a = acc_map[aid]
            r_score = a["risk_score"]
            r_level = a["risk_level"]
            is_f = a["is_fraud"]
        else:
            r_score = 0.15
            r_level = "Low"
            is_f = 0
        nodes_out.append({
            "data": {
                "id": str(aid),
                "label": f"ACC-{aid}",
                "risk": r_score,
                "risk_level": r_level,
                "gnn_prob": round(r_score * 100, 1),
                "rule_score": int(r_score * 85),
                "is_fraud": is_f
            }
        })

    edges_out = [{
        "data": {
            "id": f"tx-{t['tx_id']}",
            "source": str(t["source_id"]),
            "target": str(t["target_id"]),
            "amount": t["amount"],
            "timestamp": str(t["timestamp"]),
            "transaction_type": t["tx_type"],
            "scenario": t.get("tx_type", "transfer"),
            "is_fraud": t["is_fraud"]
        }
    } for t in selected_txs]

    return {
        "nodes": nodes_out,
        "edges": edges_out,
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
        seen_tx = set()

        for _ in range(max(1, min(hops, 2))):
            placeholders = ",".join("?" for _ in current_ids)
            c.execute(f"""
                SELECT tx_id, source_id, target_id, amount, tx_type, timestamp, is_fraud
                FROM investigation_transactions
                WHERE tier = ? AND (source_id IN ({placeholders}) OR target_id IN ({placeholders}))
                LIMIT ?
            """, [tier, *list(current_ids), *list(current_ids), limit])
            step_tx = [dict(r) for r in c.fetchall()]
            for t in step_tx:
                if t["tx_id"] not in seen_tx:
                    seen_tx.add(t["tx_id"])
                    collected_tx.append(t)
                    current_ids.add(str(t["source_id"]))
                    current_ids.add(str(t["target_id"]))

        placeholders = ",".join("?" for _ in current_ids)
        c.execute(f"SELECT * FROM investigation_accounts WHERE tier = ? AND account_id IN ({placeholders})", [tier, *list(current_ids)])
        acc_rows = [dict(r) for r in c.fetchall()]
        acc_dict = {str(a["account_id"]): a for a in acc_rows}

    # If neither transactions found nor root account exists in tier, return empty
    if str(account_id) not in current_ids and str(account_id) not in acc_dict and not collected_tx:
        return {"nodes": [], "edges": []}

    nodes_out = []
    for aid in current_ids:
        if aid in acc_dict:
            a = acc_dict[aid]
            r_score = a.get("risk_score", 0.1)
            r_level = a.get("risk_level", "Low")
            is_f = a.get("is_fraud", 0)
        else:
            r_score = 0.15
            r_level = "Low"
            is_f = 0
        nodes_out.append({
            "data": {
                "id": str(aid),
                "label": f"ACC-{aid}",
                "risk": r_score,
                "risk_level": r_level,
                "gnn_prob": round(r_score * 100, 1),
                "rule_score": int(r_score * 85),
                "is_fraud": is_f,
                "is_root": str(aid) == str(account_id)
            }
        })

    edges_out = [{
        "data": {
            "id": f"tx-{t['tx_id']}",
            "source": str(t["source_id"]),
            "target": str(t["target_id"]),
            "amount": t["amount"],
            "timestamp": str(t["timestamp"]),
            "transaction_type": t["tx_type"],
            "scenario": t.get("tx_type", "transfer"),
            "is_fraud": t["is_fraud"]
        }
    } for t in collected_tx]

    return {
        "nodes": nodes_out,
        "edges": edges_out,
        "root_account": str(account_id),
        "tier": tier
    }

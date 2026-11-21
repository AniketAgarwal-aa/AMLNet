"""Explainable AI (XAI) engine for AML risk scoring and typology attribution."""
from typing import Dict, Any, List
import numpy as np

def explain_account_risk(account: Any, alerts: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate an explainable AI report for an account.
    Strictly separates:
    1. Ground-truth label (historical record, not used in inference)
    2. Rule evidence (deterministic typology hits: circular, rapid transfer, fan-in, fan-out)
    3. Feature attribution / correlated signals (numerical deviations from normal baseline)
    4. Model prediction probability (statistical output of GNN/ML)
    """
    features = account.features or {}

    # 1. Rule Evidence
    rule_signals = []
    if alerts:
        for alt in alerts:
            if account.id in alt.get('account_ids', []):
                rule_signals.append({
                    "type": "rule_hit",
                    "typology": alt.get('pattern_type', 'unknown').replace('_', ' ').title(),
                    "risk_level": alt.get('risk_level', 'Medium'),
                    "explanation": alt.get('explanation', ''),
                    "transaction_count": len(alt.get('transaction_ids', [])),
                    "amount": alt.get('amount', 0.0)
                })

    # 2. Correlated Feature Signals
    feature_signals = []
    inc_count = features.get('incoming_count', 0)
    out_count = features.get('outgoing_count', 0)
    in_out_ratio = features.get('in_out_ratio', 1.0)
    rapid = features.get('rapid_transfer_count', 0)
    circular = features.get('circular_participation', 0)
    counterparties = features.get('unique_counterparties', 0)

    if circular > 0:
        feature_signals.append({
            "feature": "circular_participation",
            "weight": "High Impact",
            "observation": f"Participated in a closed transaction cycle involving multiple counterparties.",
            "caveat": "Correlated topological structure; does not conclusively establish criminal intent."
        })
    if rapid >= 2:
        feature_signals.append({
            "feature": "rapid_transfer_count",
            "weight": "High Impact",
            "observation": f"{rapid} sequential outbound transfers occurred within a 30-minute interval.",
            "caveat": "Indicative of pass-through / layering behavior, but can also occur in automated payroll/batch settlements."
        })
    if counterparties >= 5:
        feature_signals.append({
            "feature": "unique_counterparties",
            "weight": "Moderate Impact",
            "observation": f"Transacted with {int(counterparties)} unique counterparties.",
            "caveat": "High connectivity in graph topology expands GNN neighborhood influence."
        })
    if in_out_ratio > 4.0 or in_out_ratio < 0.25:
        feature_signals.append({
            "feature": "in_out_ratio",
            "weight": "Moderate Impact",
            "observation": f"Significant flow imbalance: incoming to outgoing amount ratio is {in_out_ratio:.2f}.",
            "caveat": "Large deposits without proportional outflows or rapid emptying of accounts."
        })

    # 3. Model Attribution Breakdown
    gnn_prob = getattr(account, 'gnn_probability', 0.0) or 0.0
    rule_score = getattr(account, 'rule_score', 0.0) or 0.0
    final_risk = getattr(account, 'final_risk', 0.0) or 0.0

    model_contribution_pct = 70.0 * gnn_prob
    rule_contribution_pct = 30.0 * (rule_score / 100.0)

    attribution = {
        "gnn_weight_factor": 0.70,
        "rule_weight_factor": 0.30,
        "gnn_contribution_points": round(model_contribution_pct, 1),
        "rule_contribution_points": round(rule_contribution_pct, 1),
        "combined_final_risk": round(final_risk, 1),
        "model_confidence_description": "High Suspicion" if gnn_prob >= 0.7 else "Moderate Suspicion" if gnn_prob >= 0.4 else "Low Suspicion"
    }

    return {
        "account_id": account.id,
        "risk_level": getattr(account, 'risk_level', 'Low'),
        "ground_truth_label": "Suspicious / SAR" if getattr(account, 'label', 0) == 1 else "Normal",
        "ground_truth_note": "For research validation only; hidden from production inference.",
        "rule_evidence": rule_signals,
        "correlated_features": feature_signals,
        "model_attribution": attribution,
        "methodology_disclaimer": "Explanations provide qualitative risk context for human investigator review. Statistical correlations do not constitute legal proof of financial crime."
    }

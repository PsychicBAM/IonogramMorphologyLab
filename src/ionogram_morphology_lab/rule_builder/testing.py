from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any
from .conditions import evaluate_conditions
from .model import ScientificRule
def run_rule_on_features(rule: ScientificRule, features: dict[str, Any]) -> bool: return rule.enabled and evaluate_conditions(features,rule.conditions)
def threshold_sweep(rule: ScientificRule, rows: list[dict[str, Any]], feature: str, values: list[float]) -> list[dict[str, Any]]:
    results=[]
    for value in values:
        clone=ScientificRule.from_dict(rule.to_dict())
        for c in clone.conditions:
            if c.get("feature")==feature: c["value"]=value
        results.append({"threshold":value,"fired":sum(run_rule_on_features(clone,r) for r in rows),"total":len(rows)})
    return results
def confusion_vs_labels(rule: ScientificRule, rows: list[dict[str, Any]], label_key: str="label") -> dict[str,int]:
    cm=Counter()
    for row in rows: cm[("positive" if run_rule_on_features(rule,row) else "negative", str(row.get(label_key)))] += 1
    return {f"{p}:{a}":n for (p,a),n in sorted(cm.items())}
def date_grouped_split(rows: list[dict[str, Any]], date_key: str="date", test_fraction: float=.2) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    groups=sorted({str(row.get(date_key,"")) for row in rows}); n=max(1,round(len(groups)*test_fraction)); test_dates=set(groups[-n:]); return [r for r in rows if str(r.get(date_key,"")) not in test_dates],[r for r in rows if str(r.get(date_key,"")) in test_dates]

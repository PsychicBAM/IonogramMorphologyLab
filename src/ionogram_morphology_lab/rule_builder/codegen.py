from __future__ import annotations
from .model import ScientificRule
def _expr(rule: ScientificRule, language: str) -> str:
    parts=[]
    symbols={"eq":"==","ne":"!=","gt":">","gte":">=","lt":"<","lte":"<="}
    for c in rule.conditions:
        if "any_of" in c: raise ValueError("Code generation does not support nested any_of")
        op=c.get("operator", "gte"); feature=repr(c["feature"]); value=repr(c.get("value"))
        if op == "exists": parts.append((f"isfield(features, {feature})" if language == "matlab" else f"{feature} in features")); continue
        if op not in symbols: raise ValueError(f"Unsupported codegen operator: {op}")
        access = f"getfield(features, {feature})" if language == "matlab" else f"features.get({feature})"
        parts.append(f"{access} {symbols[op]} {value}")
    return (" && " if language == "matlab" else " and ").join(parts) or "true"
def generate_python_rule(rule: ScientificRule) -> str:
    return f"def {rule.rule_id.lower()}(features):\n    return {_expr(rule, 'python')}\n"
def generate_matlab_function(rule: ScientificRule) -> str:
    return f"function fired = {rule.rule_id.lower()}(features)\nfired = {_expr(rule, 'matlab')};\nend\n"

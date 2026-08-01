"""Versioned JSON store for user-defined scientific rules."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ionogram_morphology_lab.utils.paths import app_root, ensure_dir

from .model import ScientificRule


def user_rules_dir() -> Path:
    return ensure_dir(app_root() / "user_library" / "rules")


def project_matlab_user_methods_dir(project_root: Path | str | None = None) -> Path:
    if project_root:
        return ensure_dir(Path(project_root) / "matlab_user_methods")
    return ensure_dir(app_root() / "user_library" / "matlab_methods")


def rule_path(rule_id: str, version: str) -> Path:
    safe_v = version.replace("/", "_")
    return user_rules_dir() / f"{rule_id}-{safe_v}.json"


def save_rule(rule: ScientificRule) -> Path:
    path = rule_path(rule.rule_id, rule.version)
    path.write_text(json.dumps(rule.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_rule(rule_id: str, version: str) -> ScientificRule:
    return ScientificRule.from_dict(json.loads(rule_path(rule_id, version).read_text(encoding="utf-8")))


def list_stored_rules() -> list[Path]:
    return sorted(user_rules_dir().glob("*.json"))


class RuleStore:
    """GUI-facing versioned rule store."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root else user_rules_dir()
        ensure_dir(self.root)
        self._history = ensure_dir(self.root / "_history")

    def list_rules(self) -> list[ScientificRule]:
        latest: dict[str, ScientificRule] = {}
        for path in sorted(self.root.glob("*.json")):
            try:
                rule = ScientificRule.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            prev = latest.get(rule.rule_id)
            if prev is None or rule.version >= prev.version:
                latest[rule.rule_id] = rule
        return sorted(latest.values(), key=lambda r: r.rule_id)

    def save_rule(self, rule: ScientificRule, comment: str = "") -> Path:
        # bump patch version timestamp for versioning
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base = rule.version.split("+")[0] or "1.1.0"
        rule.version = f"{base}+{ts}"
        path = self.root / f"{rule.rule_id}.json"
        path.write_text(json.dumps(rule.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        hist = self._history / f"{rule.rule_id}-{ts}.json"
        payload = rule.to_dict()
        payload["_change_comment"] = comment
        hist.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def disable_rule(self, rule_id: str, comment: str = "") -> Path:
        """Disable the latest local rule while preserving a versioned audit snapshot."""
        for rule in self.list_rules():
            if rule.rule_id == rule_id:
                rule.enabled = False
                rule.status = "disabled"
                return self.save_rule(rule, comment or "disabled")
        raise KeyError(f"Unknown rule: {rule_id}")

    def history(self, rule_id: str) -> list[dict]:
        rows = []
        for path in sorted(self._history.glob(f"{rule_id}-*.json")):
            try:
                rows.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return rows

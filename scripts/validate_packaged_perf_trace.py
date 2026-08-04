#!/usr/bin/env python3
"""Validate packaged-EXE profiler session completeness (Phase 4B.2j)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def validate_session(session_dir: Path, *, frozen_expected: bool = True) -> list[str]:
    errors: list[str] = []
    manifest_path = session_dir / "session_manifest.json"
    if not manifest_path.is_file():
        return [f"missing session_manifest.json in {session_dir}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    identity = manifest.get("identity") or {}
    cache_root = str(identity.get("resolved_cache_root") or identity.get("cache_root") or "")
    if frozen_expected or identity.get("frozen"):
        low = cache_root.replace("/", "\\").lower()
        if "pytest-of-" in low or "test_cache_" in low or "\\pytest-" in low:
            errors.append(f"cache root points to pytest/test path: {cache_root}")

    timeline = _load_jsonl(session_dir / "timeline.jsonl")
    spans = [r for r in timeline if "duration_s" in r]
    by_parent: dict[str | None, list[dict]] = defaultdict(list)
    by_name: dict[str, list[dict]] = defaultdict(list)
    for s in spans:
        by_parent[s.get("parent")].append(s)
        by_name[str(s.get("event"))].append(s)

    def _explained(parent_name: str, min_ratio: float = 0.90) -> None:
        parents = by_name.get(parent_name) or []
        if not parents:
            return
        parent = max(parents, key=lambda r: float(r.get("duration_s") or 0))
        dur = float(parent.get("duration_s") or 0)
        if dur < 0.5:
            return
        children = by_parent.get(parent_name) or []
        # Also include nested names that start with prefix
        child_sum = sum(float(c.get("duration_s") or 0) for c in children)
        # Fallback: sum spans whose parents list contains parent_name
        if child_sum <= 0:
            for s in spans:
                parents_list = s.get("parents") or []
                if parent_name in parents_list and s.get("event") != parent_name:
                    child_sum += float(s.get("duration_s") or 0)
        ratio = child_sum / dur if dur > 0 else 0.0
        if ratio < min_ratio:
            errors.append(
                f"parent span {parent_name}={dur:.3f}s only {ratio:.0%} explained by children "
                f"(need ≥{min_ratio:.0%})"
            )

    _explained("language_switch", 0.90)
    _explained("page_activation", 0.90)
    _explained("v2.pre_submit", 0.90)
    _explained("v2.post_result", 0.90)

    # Language must have component breakdown
    lang_parents = by_name.get("language_switch") or []
    if lang_parents and float(max(lang_parents, key=lambda r: r.get("duration_s", 0)).get("duration_s", 0)) >= 0.2:
        lang_children = [s for s in spans if (s.get("parent") == "language_switch") or ("language_switch" in (s.get("parents") or []))]
        if len(lang_children) < 3:
            errors.append("language_switch lacks page/component nested breakdown")

    # Page activation breakdown
    act = by_name.get("page_activation") or []
    if act and float(max(act, key=lambda r: r.get("duration_s", 0)).get("duration_s", 0)) >= 0.5:
        nav_children = [s for s in spans if str(s.get("event", "")).startswith("nav.")]
        if len(nav_children) < 3:
            errors.append("page_activation lacks navigation/layout nested breakdown")

    # V2 pre/post breakdown when a V2 run is present
    events = {str(s.get("event")) for s in timeline}
    v2_events = {e for e in events if e.startswith("v2.") or e.startswith("v2_")}
    if any(e.startswith("v2.pre") or e == "v2_worker_state" or e == "v2_cache_diagnose" for e in events):
        pre = [s for s in spans if str(s.get("event", "")).startswith("v2.pre")]
        post = [s for s in spans if str(s.get("event", "")).startswith("v2.post")]
        if len(pre) < 2:
            errors.append("V2 request lacks pre-submit nested breakdown")
        if "v2.post_result" in events or "v2.post_result_cached" in events:
            if len(post) < 2:
                errors.append("V2 request lacks post-result nested breakdown")

    # File I/O health
    fio = _load_jsonl(session_dir / "file_io.jsonl")
    summary_path = session_dir / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        health = summary.get("profiler_health") or {}
        if health.get("file_io_tracer_active") and health.get("file_io_records", 0) == 0:
            # Only fail if scenario likely read files (has v2/cache/page events)
            if any(x in events for x in ("fd_activate", "page_activation", "v2_worker_state", "language_switch")):
                errors.append("file_io.jsonl empty while tracer active during file-reading scenario")
    elif not fio:
        # No summary yet — still warn if timeline suggests work
        if spans and not fio:
            errors.append("file_io.jsonl empty (tracer may be inactive or broken)")

    # Heartbeat threshold soft check (report, not always fail for cold start)
    hb = _load_jsonl(session_dir / "ui_heartbeat.jsonl")
    if hb:
        delays = [float(r.get("delay_s") or 0) for r in hb]
        mx = max(delays) if delays else 0.0
        if mx > 2.0:
            errors.append(f"UI heartbeat max gap {mx:.3f}s exceeds 2.0s acceptance")

    # Warm-UI MAT policy: language / light source-strip spans must not open source MAT
    mat_ops = [
        r
        for r in fio
        if str(r.get("category") or "") == "source_mat"
        or str(r.get("path") or "").lower().endswith(".mat")
    ]
    banned_parents = ("language_switch", "lang.source_strips_visible", "nav.source_strip_light")
    for r in mat_ops:
        parents = r.get("parents") or []
        parent = r.get("parent")
        if parent in banned_parents or any(p in banned_parents for p in parents):
            errors.append(
                f"source_mat I/O under warm UI span parent={parent}: {r.get('op')} {r.get('path')}"
            )

    _ = v2_events  # reserved for future stricter checks
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session_dir", type=Path, nargs="?", help="workspaces/_packaged_exe_perf/<stamp>")
    ap.add_argument("--allow-dev", action="store_true", help="Do not require frozen cache policy")
    args = ap.parse_args(argv)
    if args.session_dir is None:
        root = Path("workspaces") / "_packaged_exe_perf"
        if not root.is_dir():
            print("FAIL: no session_dir and workspaces/_packaged_exe_perf missing")
            return 2
        sessions = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name)
        if not sessions:
            print("FAIL: no profiler sessions found")
            return 2
        args.session_dir = sessions[-1]
    errs = validate_session(args.session_dir, frozen_expected=not args.allow_dev)
    if errs:
        print(f"FAIL packaged perf trace: {args.session_dir}")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK packaged perf trace: {args.session_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

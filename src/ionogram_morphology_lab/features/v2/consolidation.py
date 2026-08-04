"""Explainable centerline/component consolidation — not an arbitrary hard cap."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from ionogram_morphology_lab.features.v2.types import CenterlineRecord

# Scientific plausibility: a typical ionogram may show a few real branches
# (O/X, multiple hops, layers). Counts above this are warned, not clipped.
PLAUSIBILITY_WARNING_ABOVE = 16
# When consolidated count still exceeds this, mark oversegmentation suspected.
OVERSEG_SUSPECT_ABOVE = 8
# Fragmentation score = raw/consolidated; above this with high raw → suspect
FRAGMENTATION_RATIO_SUSPECT = 3.0


@dataclass
class ComponentDecision:
    component_id: int
    decision: str  # accepted | rejected | merged
    reasons: list[str]
    branch_id: int | None = None
    merged_into_branch: int | None = None
    merge_partners: list[int] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConsolidationResult:
    raw_centerlines: list[CenterlineRecord]
    consolidated_centerlines: list[CenterlineRecord]
    decisions: list[ComponentDecision]
    raw_component_count: int
    consolidated_branch_count: int
    rejected_component_count: int
    consolidation_count: int
    fragmentation_score: float
    oversegmentation_suspected: bool
    plausibility_warning: bool
    branch_labels: np.ndarray
    notes: list[str] = field(default_factory=list)

    def to_serializable(self) -> dict[str, Any]:
        return {
            "raw_component_count": self.raw_component_count,
            "consolidated_branch_count": self.consolidated_branch_count,
            "rejected_component_count": self.rejected_component_count,
            "consolidation_count": self.consolidation_count,
            "fragmentation_score": self.fragmentation_score,
            "oversegmentation_suspected": self.oversegmentation_suspected,
            "plausibility_warning": self.plausibility_warning,
            "plausibility_warning_above": PLAUSIBILITY_WARNING_ABOVE,
            "overseg_suspect_above": OVERSEG_SUSPECT_ABOVE,
            "decisions": [d.to_dict() for d in self.decisions],
            "notes": list(self.notes),
            "raw_centerlines": [c.to_dict() for c in self.raw_centerlines],
            "consolidated_centerlines": [c.to_dict() for c in self.consolidated_centerlines],
        }


def evaluate_oversegmentation(
    cons: ConsolidationResult,
    *,
    accepted: np.ndarray,
    floor: np.ndarray,
    centerlines: list[CenterlineRecord],
    shape: tuple[int, int],
) -> tuple[bool, dict[str, Any]]:
    """Oversegmentation from multiple evidence channels — not consolidated count alone."""
    h, w = shape
    floor_h = max(2, h // 12)
    cons_n = len(centerlines)
    pre_n = cons.raw_component_count
    frag = float(pre_n / max(cons_n, 1)) if pre_n else 0.0
    floor_pix_frac = float((accepted & floor).sum() / max(int(accepted.sum()), 1)) if accepted.any() else 0.0
    above = accepted.copy()
    above[:floor_h, :] = False
    coverage_above = float(above.mean()) if above.size else 0.0
    # Floor-ish branches: median row in floor band
    floor_branches = 0
    small_isolated = 0
    for cl in centerlines:
        if not cl.points_rc:
            continue
        med_r = float(np.median([r for r, _ in cl.points_rc]))
        if med_r <= floor_h:
            floor_branches += 1
        if cl.point_count < 12 and (cl.frequency_span_bins[1] - cl.frequency_span_bins[0]) < 15:
            small_isolated += 1
    spatial_implausible = cons_n >= 6 and coverage_above < 0.002
    reasons = []
    if floor_pix_frac >= 0.25:
        reasons.append("floor_dominated_accepted_pixels")
    if floor_branches >= 1:
        reasons.append("floor_branch_count")
    if small_isolated >= 3:
        reasons.append("unsupported_isolated_branches")
    if spatial_implausible:
        reasons.append("spatial_branch_plausibility")
    if frag >= FRAGMENTATION_RATIO_SUSPECT and pre_n >= 20:
        reasons.append("fragmentation_score")
    if coverage_above < 0.001 and cons_n > 0:
        reasons.append("trace_coverage_above_floor")
    if cons_n > OVERSEG_SUSPECT_ABOVE:
        reasons.append("consolidated_count_high")
    if small_isolated >= 2 and cons_n >= 4:
        reasons.append("disconnected_small_branches")
    suspected = bool(reasons)
    meta = {
        "suspected": suspected,
        "reasons": reasons,
        "floor_dominated_accepted_fraction": floor_pix_frac,
        "floor_branch_count": floor_branches,
        "unsupported_isolated_branches": small_isolated,
        "fragmentation_score": frag,
        "trace_coverage_above_floor": coverage_above,
        "consolidated_branch_count": cons_n,
        "preconsolidation_centerline_count": pre_n,
    }
    return suspected, meta


def consolidate_centerlines(
    raw_centerlines: list[CenterlineRecord],
    *,
    snr: np.ndarray,
    interference: np.ndarray,
    shape: tuple[int, int],
    prior_rejections: list[dict[str, Any]] | None = None,
    floor_mask: np.ndarray | None = None,
) -> ConsolidationResult:
    """
    Merge fragmented ridge pieces into branches using explainable evidence.

    Does not apply a hard cap on count. Emits oversegmentation_suspected when
    consolidation cannot reduce fragmentation to a plausible branch set.
    """
    h, w = shape
    decisions: list[ComponentDecision] = []
    notes: list[str] = []

    # Seed prior small/not-ridge rejections into the decision log
    for pr in prior_rejections or []:
        decisions.append(
            ComponentDecision(
                component_id=int(pr.get("id", -1)),
                decision="rejected",
                reasons=[str(pr.get("reason", "prior_reject"))],
                metrics={k: v for k, v in pr.items() if k not in ("id", "reason", "accepted")},
            )
        )

    # Stage 1: reject low-support / interference-dominated / low-continuity raw pieces
    survivors: list[CenterlineRecord] = []
    for cl in raw_centerlines:
        reasons: list[str] = []
        conf = _component_confidence(cl, snr)
        metrics = {
            "point_count": cl.point_count,
            "continuity": cl.continuity,
            "gap_fraction": cl.gap_fraction,
            "interference_overlap": cl.interference_overlap,
            "component_confidence": conf,
            "freq_span": list(cl.frequency_span_bins),
            "height_span": list(cl.height_span_bins),
        }
        if cl.point_count < 8:
            reasons.append("minimum_supported_length")
        if cl.continuity < 0.40:
            reasons.append("minimum_continuity")
        if cl.interference_overlap > 0.45:
            reasons.append("interference_exclusion")
        if conf < 0.30:
            reasons.append("low_component_confidence")
        if getattr(cl, "floor_overlap_fraction", 0.0) >= 0.55:
            reasons.append("floor_component")
        # Floor-like: median row in floor band without support above
        if cl.points_rc:
            med_r = float(np.median([r for r, _ in cl.points_rc]))
            if med_r <= max(4, h // 12) and (cl.frequency_span_bins[1] - cl.frequency_span_bins[0]) < 20:
                reasons.append("floor_component")
        if (cl.frequency_span_bins[1] - cl.frequency_span_bins[0]) < 6 and (
            cl.height_span_bins[1] - cl.height_span_bins[0]
        ) < 6:
            reasons.append("low_support_noise_component")
        _ = floor_mask  # reserved for future pixel-level merge gating

        if reasons:
            decisions.append(
                ComponentDecision(
                    component_id=cl.component_id,
                    decision="rejected",
                    reasons=reasons,
                    metrics=metrics,
                )
            )
        else:
            survivors.append(cl)

    rejected_count = sum(1 for d in decisions if d.decision == "rejected")

    # Stage 2: greedy merge of compatible fragments into branches
    unused = list(survivors)
    branches: list[list[CenterlineRecord]] = []
    merge_events = 0

    # Prefer longer fragments as seeds
    unused.sort(key=lambda c: c.point_count, reverse=True)
    while unused:
        seed = unused.pop(0)
        group = [seed]
        changed = True
        while changed:
            changed = False
            keep: list[CenterlineRecord] = []
            for cand in unused:
                ok, why = _compatible_merge(group, cand, snr)
                if ok:
                    group.append(cand)
                    merge_events += 1
                    decisions.append(
                        ComponentDecision(
                            component_id=cand.component_id,
                            decision="merged",
                            reasons=why,
                            merge_partners=[g.component_id for g in group if g.component_id != cand.component_id],
                            metrics={
                                "point_count": cand.point_count,
                                "component_confidence": _component_confidence(cand, snr),
                            },
                        )
                    )
                    changed = True
                else:
                    keep.append(cand)
            unused = keep
        branches.append(group)

    # Stage 2b: merge nearly-coincident consolidated groups (same ridge, label split)
    branches = _merge_near_coincident_groups(branches, snr)

    # Mark seed/accepted members that were not already logged as merged
    logged_ids = {d.component_id for d in decisions}
    consolidated: list[CenterlineRecord] = []
    branch_labels = np.zeros((h, w), dtype=np.int32)

    for bid, group in enumerate(branches, start=1):
        merged_cl = _merge_group_to_centerline(group, snr, interference, branch_id=bid)
        consolidated.append(merged_cl)
        for g in group:
            if g.component_id not in logged_ids:
                decisions.append(
                    ComponentDecision(
                        component_id=g.component_id,
                        decision="accepted",
                        reasons=["branch_seed" if g is group[0] else "compatible_fragment_kept"],
                        branch_id=bid,
                        metrics={
                            "point_count": g.point_count,
                            "component_confidence": _component_confidence(g, snr),
                        },
                    )
                )
                logged_ids.add(g.component_id)
            else:
                # Update merged decision with final branch id
                for d in decisions:
                    if d.component_id == g.component_id and d.decision == "merged":
                        d.merged_into_branch = bid
                        d.branch_id = bid
        for r, c in merged_cl.points_rc:
            if 0 <= r < h and 0 <= c < w:
                branch_labels[r, c] = bid
            # thicken label slightly for visibility / area stats
            for dr in (-1, 0, 1):
                rr = r + dr
                if 0 <= rr < h and 0 <= c < w and branch_labels[rr, c] == 0:
                    branch_labels[rr, c] = bid

    raw_n = len(raw_centerlines)
    cons_n = len(consolidated)
    frag = float(raw_n / max(cons_n, 1)) if raw_n else 0.0
    # Merges = survivors that did not become their own singleton seed count
    consolidation_count = max(merge_events, max(0, len(survivors) - cons_n))

    overseg = bool(
        cons_n > OVERSEG_SUSPECT_ABOVE
        or (raw_n >= 25 and frag >= FRAGMENTATION_RATIO_SUSPECT and cons_n > 6)
        or (raw_n >= 40 and cons_n > 8)
    )
    plaus_warn = cons_n > PLAUSIBILITY_WARNING_ABOVE or raw_n > PLAUSIBILITY_WARNING_ABOVE
    if overseg:
        notes.append("oversegmentation_suspected")
    if plaus_warn:
        notes.append(f"plausibility_warning_above_{PLAUSIBILITY_WARNING_ABOVE}")

    return ConsolidationResult(
        raw_centerlines=list(raw_centerlines),
        consolidated_centerlines=consolidated,
        decisions=decisions,
        raw_component_count=raw_n,
        consolidated_branch_count=cons_n,
        rejected_component_count=rejected_count,
        consolidation_count=consolidation_count,
        fragmentation_score=frag,
        oversegmentation_suspected=overseg,
        plausibility_warning=plaus_warn,
        branch_labels=branch_labels,
        notes=notes,
    )


def _merge_near_coincident_groups(
    branches: list[list[CenterlineRecord]],
    snr: np.ndarray,
) -> list[list[CenterlineRecord]]:
    """Second pass: merge groups that are vertically coincident on overlapping columns."""
    if len(branches) <= 1:
        return branches
    # Build temporary centerlines for comparison
    temps = [_merge_group_to_centerline(g, snr, np.zeros_like(snr, dtype=bool), branch_id=i + 1)
             for i, g in enumerate(branches)]
    parent = list(range(len(branches)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(temps)):
        for j in range(i + 1, len(temps)):
            a, b = temps[i], temps[j]
            ma = {c: r for r, c in a.points_rc}
            mb = {c: r for r, c in b.points_rc}
            common = set(ma) & set(mb)
            gap = _freq_gap(a, b)
            slope_ok = abs(a.slope - b.slope) <= 0.8
            if common:
                med = float(np.median([abs(ma[c] - mb[c]) for c in common]))
                # Only merge near-coincident fragments, never parallel branches
                if med <= 2.5 and slope_ok:
                    pi, pj = find(i), find(j)
                    if pi != pj:
                        parent[pj] = pi
            elif gap <= 6 and slope_ok and _endpoint_distance(a, b) <= 10:
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pj] = pi

    buckets: dict[int, list[CenterlineRecord]] = {}
    for i, g in enumerate(branches):
        buckets.setdefault(find(i), []).extend(g)
    return list(buckets.values())


def _component_confidence(cl: CenterlineRecord, snr: np.ndarray) -> float:
    if cl.point_count <= 0:
        return 0.0
    amps = []
    for r, c in cl.points_rc:
        if 0 <= r < snr.shape[0] and 0 <= c < snr.shape[1]:
            amps.append(float(snr[r, c]))
    amp_score = float(np.clip(np.median(amps) / 5.0, 0, 1)) if amps else 0.0
    cont = float(np.clip(cl.continuity, 0, 1))
    gap = float(np.clip(1.0 - cl.gap_fraction, 0, 1))
    interf = float(np.clip(1.0 - cl.interference_overlap, 0, 1))
    length = float(np.clip(cl.point_count / 40.0, 0, 1))
    return float(0.25 * amp_score + 0.25 * cont + 0.2 * gap + 0.15 * interf + 0.15 * length)


def _compatible_merge(
    group: list[CenterlineRecord],
    cand: CenterlineRecord,
    snr: np.ndarray,
) -> tuple[bool, list[str]]:
    """Return (ok, reasons) if cand can join group as same-trace fragment."""
    reasons: list[str] = []
    # Compare against nearest group member by frequency proximity
    best = min(group, key=lambda g: _freq_gap(g, cand))
    gap = _freq_gap(best, cand)
    end_dist = _endpoint_distance(best, cand)
    slope_diff = abs(best.slope - cand.slope)
    curv_diff = abs(best.curvature - cand.curvature)

    # Distinct parallel branches: overlapping frequency with large row offset
    ma = {c: r for r, c in best.points_rc}
    mb = {c: r for r, c in cand.points_rc}
    common = set(ma) & set(mb)
    if common:
        med_sep = float(np.median([abs(ma[c] - mb[c]) for c in common]))
        if med_sep >= 6.0:
            return False, ["parallel_branch_separation"]

    # Compatible frequency spans: overlap or small/medium gap along ridge
    if gap <= 14:
        reasons.append("compatible_frequency_spans")
    elif gap <= 30 and end_dist <= 16:
        reasons.append("compatible_frequency_spans_with_gap")
    else:
        return False, ["incompatible_frequency_spans"]

    if end_dist <= 18:
        reasons.append("endpoint_proximity")
    elif gap <= 8 and end_dist <= 28:
        reasons.append("endpoint_proximity_relaxed_for_small_gap")
    else:
        return False, ["endpoint_too_far"]

    if slope_diff <= 0.65:
        reasons.append("compatible_slope")
    elif slope_diff <= 1.2 and gap <= 10:
        reasons.append("compatible_slope_relaxed")
    else:
        return False, ["incompatible_slope"]

    if curv_diff <= 2.5 or best.point_count < 8 or cand.point_count < 8:
        reasons.append("compatible_curvature")
    else:
        return False, ["incompatible_curvature"]

    if gap <= 20:
        reasons.append("small_gap")

    if _amplitude_continuity(best, cand, snr):
        reasons.append("amplitude_continuity")
    else:
        # soft: allow if other evidence strong
        if gap > 10 or end_dist > 14:
            return False, ["amplitude_discontinuity"]

    if _shared_ridge_hint(best, cand):
        reasons.append("shared_ridge_structure")

    return True, reasons


def _freq_gap(a: CenterlineRecord, b: CenterlineRecord) -> int:
    a0, a1 = a.frequency_span_bins
    b0, b1 = b.frequency_span_bins
    if a1 < b0:
        return int(b0 - a1)
    if b1 < a0:
        return int(a0 - b1)
    return 0  # overlap


def _endpoint_distance(a: CenterlineRecord, b: CenterlineRecord) -> float:
    if not a.points_rc or not b.points_rc:
        return 1e9
    ends_a = [a.points_rc[0], a.points_rc[-1]]
    ends_b = [b.points_rc[0], b.points_rc[-1]]
    best = 1e9
    for ra, ca in ends_a:
        for rb, cb in ends_b:
            best = min(best, float(np.hypot(ra - rb, ca - cb)))
    return best


def _amplitude_continuity(a: CenterlineRecord, b: CenterlineRecord, snr: np.ndarray) -> bool:
    def _end_amp(cl: CenterlineRecord, which: str) -> float:
        pts = cl.points_rc[:3] if which == "start" else cl.points_rc[-3:]
        vals = [float(snr[r, c]) for r, c in pts if 0 <= r < snr.shape[0] and 0 <= c < snr.shape[1]]
        return float(np.median(vals)) if vals else 0.0

    # Compare nearest ends by column
    if a.frequency_span_bins[1] <= b.frequency_span_bins[0]:
        aa, bb = _end_amp(a, "end"), _end_amp(b, "start")
    elif b.frequency_span_bins[1] <= a.frequency_span_bins[0]:
        aa, bb = _end_amp(b, "end"), _end_amp(a, "start")
    else:
        aa = float(np.median([snr[r, c] for r, c in a.points_rc[:: max(1, len(a.points_rc)//5)]]))
        bb = float(np.median([snr[r, c] for r, c in b.points_rc[:: max(1, len(b.points_rc)//5)]]))
    if max(aa, bb) <= 1e-9:
        return True
    ratio = min(aa, bb) / max(aa, bb)
    return ratio >= 0.35


def _shared_ridge_hint(a: CenterlineRecord, b: CenterlineRecord) -> bool:
    # Overlapping columns with similar row → same ridge
    ma = {c: r for r, c in a.points_rc}
    mb = {c: r for r, c in b.points_rc}
    common = set(ma) & set(mb)
    if not common:
        return _freq_gap(a, b) <= 8
    diffs = [abs(ma[c] - mb[c]) for c in common]
    return float(np.median(diffs)) <= 4.0


def _merge_group_to_centerline(
    group: list[CenterlineRecord],
    snr: np.ndarray,
    interference: np.ndarray,
    *,
    branch_id: int,
) -> CenterlineRecord:
    # Union points by column (SNR-weighted row)
    col_rows: dict[int, list[tuple[int, float]]] = {}
    for cl in group:
        for r, c in cl.points_rc:
            w = float(snr[r, c]) if 0 <= r < snr.shape[0] and 0 <= c < snr.shape[1] else 0.0
            col_rows.setdefault(int(c), []).append((int(r), max(w, 1e-6)))
    points: list[tuple[int, int]] = []
    for c in sorted(col_rows):
        rows, weights = zip(*col_rows[c])
        r = int(np.round(np.average(rows, weights=weights)))
        points.append((r, c))

    if not points:
        return CenterlineRecord(
            branch_id=branch_id,
            component_id=group[0].component_id,
            points_rc=[],
            frequency_span_bins=(0, 0),
            height_span_bins=(0, 0),
            point_count=0,
            continuity=0.0,
            gap_fraction=1.0,
            slope=0.0,
            curvature=0.0,
            interference_overlap=0.0,
            quality_status="invalid",
        )

    rs = np.array([p[0] for p in points], dtype=float)
    cs = np.array([p[1] for p in points], dtype=float)
    span_c = (int(cs.min()), int(cs.max()))
    span_r = (int(rs.min()), int(rs.max()))
    expected = max(int(cs.max() - cs.min()) + 1, 1)
    # count gaps
    gaps = 0
    prev = None
    for c in cs.astype(int):
        if prev is not None and c - prev > 1:
            gaps += int(c - prev - 1)
        prev = int(c)
    continuity = len(points) / expected
    gap_fraction = gaps / expected
    slope = float(np.polyfit(cs, rs, 1)[0]) if len(points) >= 2 else 0.0
    if len(points) >= 3:
        curvature = float(np.mean(np.abs(np.diff(np.diff(rs)))))
    else:
        curvature = 0.0
    ov = float(np.mean([interference[r, c] for r, c in points])) if points else 0.0
    q = "good" if continuity > 0.7 and ov < 0.2 else ("partial" if continuity > 0.4 else "poor")
    return CenterlineRecord(
        branch_id=branch_id,
        component_id=group[0].component_id,
        points_rc=points,
        frequency_span_bins=span_c,
        height_span_bins=span_r,
        point_count=len(points),
        continuity=float(continuity),
        gap_fraction=float(gap_fraction),
        slope=slope,
        curvature=curvature,
        interference_overlap=ov,
        quality_status=q,
        member_component_ids=[g.component_id for g in group],
        component_confidence=float(np.mean([_component_confidence(g, snr) for g in group])),
    )

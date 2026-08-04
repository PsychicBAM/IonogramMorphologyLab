"""Branch / alternative structure measurements (candidate interpretations)."""

from __future__ import annotations

import numpy as np

from ionogram_morphology_lab.features.v2.types import CenterlineRecord, MeasuredFeature


def measure_branches(
    branch_labels: np.ndarray,
    centerlines: list[CenterlineRecord],
    accepted: np.ndarray,
    *,
    oversegmentation_suspected: bool = False,
    raw_component_count: int | None = None,
) -> dict[str, MeasuredFeature]:
    feats: dict[str, MeasuredFeature] = {}
    n_comp = int(raw_component_count) if raw_component_count is not None else int(
        len({int(v) for v in np.unique(branch_labels) if int(v) > 0})
    )
    n_branch = len(centerlines)

    feats["v2_component_count"] = MeasuredFeature(
        "v2_component_count", float(n_comp), unit="count", valid=True, confidence_status="high",
        metadata={"alias_of": "v2_raw_component_count"},
    )
    feats["v2_branch_count"] = MeasuredFeature(
        "v2_branch_count", float(n_branch), unit="count", valid=True,
        confidence_status="low" if oversegmentation_suspected else "high",
        metadata={
            "note": "branch_count_alone_does_not_prove_mixed_spread",
            "oversegmentation_suspected": oversegmentation_suspected,
        },
    )

    if n_branch == 0 or oversegmentation_suspected:
        reason = "oversegmentation_suspected" if oversegmentation_suspected else "trace_not_found"
        for fid in (
            "v2_branch_separation_bins",
            "v2_branch_parallelism",
            "v2_overlapping_layer_possibility",
            "v2_multiple_reflection_possibility",
            "v2_ox_ambiguity_possibility",
            "v2_branch_relative_amplitude",
        ):
            feats[fid] = MeasuredFeature(
                fid, None, unit="", valid=False,
                reason_invalid=reason, confidence_status="abstain",
            )
        feats["v2_merge_split_locations"] = MeasuredFeature(
            "v2_merge_split_locations", None, unit="count", valid=False,
            reason_invalid=reason, confidence_status="abstain",
            metadata={"merge_split_coordinates": []},
        )
        return feats

    # Separation: median absolute row difference where columns overlap
    separations: list[float] = []
    slopes = [c.slope for c in centerlines]
    if n_branch >= 2:
        for i in range(n_branch):
            for j in range(i + 1, n_branch):
                a = {c: r for r, c in centerlines[i].points_rc}
                b = {c: r for r, c in centerlines[j].points_rc}
                common = set(a) & set(b)
                if common:
                    d = [abs(a[c] - b[c]) for c in common]
                    separations.append(float(np.median(d)))
        if separations:
            feats["v2_branch_separation_bins"] = MeasuredFeature(
                "v2_branch_separation_bins", float(np.median(separations)), unit="bins",
                valid=True, confidence_status="medium",
            )
        else:
            feats["v2_branch_separation_bins"] = MeasuredFeature(
                "v2_branch_separation_bins", None, unit="bins", valid=False,
                reason_invalid="insufficient_coverage", confidence_status="abstain",
                affected_region="no_overlapping_frequency_columns",
            )
        if len(slopes) >= 2:
            sdiff = float(np.std(slopes))
            parallelism = float(1.0 / (1.0 + sdiff))
            feats["v2_branch_parallelism"] = MeasuredFeature(
                "v2_branch_parallelism", parallelism, unit="score",
                valid=True, confidence_status="low",
            )
        else:
            feats["v2_branch_parallelism"] = MeasuredFeature(
                "v2_branch_parallelism", None, unit="score", valid=False,
                reason_invalid="insufficient_coverage", confidence_status="abstain",
            )
    else:
        feats["v2_branch_separation_bins"] = MeasuredFeature(
            "v2_branch_separation_bins", None, unit="bins", valid=False,
            reason_invalid="single_branch", confidence_status="abstain",
        )
        feats["v2_branch_parallelism"] = MeasuredFeature(
            "v2_branch_parallelism", None, unit="score", valid=False,
            reason_invalid="single_branch", confidence_status="abstain",
        )

    # Merge/split coordinates (not only count)
    merge_split_coords: list[dict[str, int]] = []
    prev = 0
    if accepted.any():
        for c in range(accepted.shape[1]):
            labs = set(int(v) for v in np.unique(branch_labels[:, c]) if int(v) > 0)
            n = len(labs)
            if prev and n and n != prev:
                rows = np.where(branch_labels[:, c] > 0)[0]
                r_med = int(np.median(rows)) if rows.size else 0
                merge_split_coords.append({"col": int(c), "row": r_med, "from_n": int(prev), "to_n": int(n)})
            prev = n or prev
    feats["v2_merge_split_locations"] = MeasuredFeature(
        "v2_merge_split_locations", float(len(merge_split_coords)), unit="count",
        valid=True, confidence_status="low",
        metadata={"candidate_interpretation": True, "merge_split_coordinates": merge_split_coords},
    )

    rel_amp = None
    if n_branch >= 2 and accepted.any():
        amps = []
        for cl in centerlines:
            mask = branch_labels == cl.branch_id
            if mask.any():
                amps.append(float(mask.sum()))
        if len(amps) >= 2 and max(amps) > 0:
            rel_amp = float(min(amps) / max(amps))
    feats["v2_branch_relative_amplitude"] = MeasuredFeature(
        "v2_branch_relative_amplitude", rel_amp, unit="ratio",
        valid=rel_amp is not None,
        reason_invalid="" if rel_amp is not None else "single_branch",
        confidence_status="low" if rel_amp is not None else "abstain",
    )

    sep_med = separations and float(np.median(separations)) or None
    overlapping = bool(sep_med is not None and 2 <= sep_med <= 25 and n_branch >= 2)
    multi_refl = bool(sep_med is not None and sep_med > 25 and n_branch >= 2)
    ox_amb = bool(
        n_branch >= 2
        and sep_med is not None
        and 3 <= sep_med <= 40
        and (feats.get("v2_branch_parallelism") and feats["v2_branch_parallelism"].valid
             and (feats["v2_branch_parallelism"].value or 0) > 0.5)
    )

    feats["v2_overlapping_layer_possibility"] = MeasuredFeature(
        "v2_overlapping_layer_possibility", float(overlapping), unit="flag",
        valid=n_branch >= 2, reason_invalid="" if n_branch >= 2 else "single_branch",
        confidence_status="low",
        metadata={"candidate_interpretation": True, "not_ox_declaration": True},
    )
    feats["v2_multiple_reflection_possibility"] = MeasuredFeature(
        "v2_multiple_reflection_possibility", float(multi_refl), unit="flag",
        valid=n_branch >= 2, reason_invalid="" if n_branch >= 2 else "single_branch",
        confidence_status="low",
        metadata={"candidate_interpretation": True},
    )
    feats["v2_ox_ambiguity_possibility"] = MeasuredFeature(
        "v2_ox_ambiguity_possibility", float(ox_amb), unit="flag",
        valid=n_branch >= 2, reason_invalid="" if n_branch >= 2 else "single_branch",
        confidence_status="low",
        metadata={
            "candidate_interpretation": True,
            "note": "Do not declare physical O/X modes from Amp_all alone",
        },
    )
    return feats

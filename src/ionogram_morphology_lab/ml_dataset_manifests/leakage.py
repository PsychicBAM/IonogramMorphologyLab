"""Deterministic leakage graph and atomic-group construction."""

from __future__ import annotations

from typing import Any

from ionogram_morphology_lab.ml_dataset_manifests.constants import (
    DEFAULT_GROUPING_POLICY,
    GROUPING_POLICIES,
)
from ionogram_morphology_lab.ml_dataset_manifests.models import AtomicGroup, ManifestItemRecord
from ionogram_morphology_lab.ml_dataset_readiness.acquisition_date import (
    is_valid_acquisition_date,
)


class UnionFind:
    def __init__(self, keys: list[str]) -> None:
        self.parent = {k: k for k in keys}
        self.rank = {k: 0 for k in keys}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def policy_relations(policy_id: str) -> tuple[list[str], list[str], list[str]]:
    """Return (included, unavailable_placeholders, fallbacks) for a policy."""
    if policy_id not in GROUPING_POLICIES:
        raise ValueError(f"Unknown grouping policy: {policy_id!r}")
    all_rels = [
        "exact_source_sha_frame",
        "related_frame_group",
        "sequence_id",
        "campaign_id",
        "source_date",
        "acquisition_period",
        "owner_protected_group",
    ]
    if policy_id == "sequence_blocked":
        included = ["exact_source_sha_frame", "sequence_id"]
    elif policy_id == "related_frame_group_blocked":
        included = ["exact_source_sha_frame", "related_frame_group"]
    elif policy_id == "source_date_blocked":
        included = ["exact_source_sha_frame", "source_date"]
    elif policy_id == "acquisition_period_blocked":
        included = ["exact_source_sha_frame", "acquisition_period", "source_date"]
    elif policy_id == "campaign_blocked":
        included = ["exact_source_sha_frame", "campaign_id"]
    elif policy_id == "manual_atomic_group_assignment":
        included = ["exact_source_sha_frame", "related_frame_group", "sequence_id"]
    else:  # conservative_combined_leakage_graph (default)
        included = [
            "exact_source_sha_frame",
            "related_frame_group",
            "sequence_id",
            "campaign_id",
            "source_date",
            "acquisition_period",
        ]
    unavailable = [r for r in all_rels if r not in included]
    fallbacks: list[str] = []
    return included, unavailable, fallbacks


def _bucket_key(item: ManifestItemRecord, relation: str) -> str | None:
    if relation == "exact_source_sha_frame":
        if not item.source_sha256:
            return None
        return f"sha_frame:{item.source_sha256}:{item.frame_index}"
    if relation == "related_frame_group":
        return f"rel:{item.related_frame_group}" if item.related_frame_group else None
    if relation == "sequence_id":
        return f"seq:{item.sequence_id}" if item.sequence_id else None
    if relation == "campaign_id":
        return f"camp:{item.campaign_id}" if item.campaign_id else None
    if relation == "source_date":
        if is_valid_acquisition_date(item.source_date):
            return f"date:{item.source_date}"
        return None
    if relation == "acquisition_period":
        period = item.acquisition_period or item.source_date
        if is_valid_acquisition_date(period):
            return f"period:{period}"
        return None
    if relation == "owner_protected_group":
        return None
    return None


def build_leakage_graph(
    items: list[ManifestItemRecord],
    *,
    policy_id: str = DEFAULT_GROUPING_POLICY,
) -> tuple[list[AtomicGroup], dict[str, Any]]:
    """Build deterministic atomic groups via union-find on protected relations."""
    included, unavailable, fallbacks = policy_relations(policy_id)
    limitations: list[str] = []
    missing_rel = 0
    missing_seq = 0
    for it in items:
        if not it.related_frame_group:
            missing_rel += 1
        if not it.sequence_id:
            missing_seq += 1
    if missing_rel:
        limitations.append(
            f"related_frame_group missing for {missing_rel} item(s); "
            "independence not assumed; coarser relations used when available"
        )
    if missing_seq:
        limitations.append(
            f"sequence_id missing for {missing_seq} item(s); "
            "frame-level independence not assumed"
        )

    keys = sorted(it.identity_key() for it in items)
    if not keys:
        meta = {
            "policy_id": policy_id,
            "included_relations": included,
            "unavailable_relations": unavailable,
            "fallback_decisions": fallbacks,
            "limitations": limitations,
            "edge_count": 0,
        }
        return [], meta

    uf = UnionFind(keys)
    by_key = {it.identity_key(): it for it in items}
    edge_notes: list[str] = []
    buckets: dict[str, list[str]] = {}

    for relation in included:
        for it in items:
            bk = _bucket_key(it, relation)
            if not bk:
                continue
            buckets.setdefault(f"{relation}|{bk}", []).append(it.identity_key())

    for bucket, members in sorted(buckets.items()):
        members = sorted(set(members))
        if len(members) < 2:
            # Still record singleton sha_frame self-identity via later component build
            continue
        root0 = members[0]
        for other in members[1:]:
            uf.union(root0, other)
            edge_notes.append(f"{bucket}:{root0}->{other}")

    # Fail closed when no defensible grouping identity can be derived for an item
    for it in items:
        if (
            not it.source_sha256
            and not it.related_frame_group
            and not it.sequence_id
            and not it.source_date
        ):
            limitations.append(
                f"fail_closed_no_grouping_identity:{it.identity_key()}"
            )
            it.identity_issues = list(it.identity_issues) + ["no_defensible_grouping"]

    components: dict[str, list[str]] = {}
    for k in keys:
        components.setdefault(uf.find(k), []).append(k)

    groups: list[AtomicGroup] = []
    for root, members in sorted(components.items(), key=lambda kv: min(kv[1])):
        members = sorted(members)
        member_items = [by_key[m] for m in members]
        states = sorted({m.contamination_state for m in member_items})
        # Mixed exposure eligibility → group not untouched-eligible
        eligible = all(m.eligible_untouched_holdout for m in member_items) and not any(
            s in {"development_exposed", "future_training_exposed", "holdout_revealed", "prohibited_invalid"}
            for s in states
        )
        if len(states) > 1 and any(
            s != "untouched_candidate" for s in states
        ):
            eligible = False
            limitations.append(
                f"mixed_exposure_in_group:{root}:states={','.join(states)}"
            )
        gid = f"ag_{deterministic_group_suffix(members)}"
        groups.append(
            AtomicGroup(
                group_id=gid,
                item_identity_keys=members,
                item_ids=sorted({m.item_id for m in member_items}),
                source_shas=sorted({m.source_sha256 for m in member_items if m.source_sha256}),
                source_dates=sorted(
                    {
                        m.source_date
                        for m in member_items
                        if is_valid_acquisition_date(m.source_date)
                    }
                ),
                sequence_ids=sorted({m.sequence_id for m in member_items if m.sequence_id}),
                related_frame_groups=sorted(
                    {m.related_frame_group for m in member_items if m.related_frame_group}
                ),
                campaign_ids=sorted({m.campaign_id for m in member_items if m.campaign_id}),
                target_labels=sorted({m.target_label for m in member_items if m.target_label}),
                contamination_states=states,
                eligible_untouched_holdout=eligible,
                grouping_edges=[e for e in edge_notes if any(m in e for m in members)][:50],
            )
        )

    # Assign atomic_group_id onto items
    key_to_gid = {}
    for g in groups:
        for ik in g.item_identity_keys:
            key_to_gid[ik] = g.group_id
    for it in items:
        it.atomic_group_id = key_to_gid.get(it.identity_key(), "")

    groups.sort(key=lambda g: g.group_id)
    meta = {
        "policy_id": policy_id,
        "included_relations": included,
        "unavailable_relations": unavailable,
        "fallback_decisions": fallbacks
        + (["coarser_source_date_when_sequence_missing"] if missing_seq else []),
        "limitations": limitations,
        "edge_count": len(edge_notes),
        "group_count": len(groups),
        "item_count": len(items),
        "deterministic_ordering": "sorted_item_identity_then_group_id",
    }
    return groups, meta


def deterministic_group_suffix(members: list[str]) -> str:
    from ionogram_morphology_lab.morphology_review_corpus.hashing import deterministic_hash

    return deterministic_hash({"members": sorted(members)})[:16]

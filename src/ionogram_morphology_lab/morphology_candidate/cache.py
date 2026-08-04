"""Separate morphology-candidate cache (does not touch V2 geometry cache)."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.morphology_candidate.reviews import ledger_hash
from ionogram_morphology_lab.morphology_candidate.types import (
    CANDIDATE_CACHE_SCHEMA_VERSION,
    CANDIDATE_ENGINE_VERSION,
    CANDIDATE_RESULT_CONTRACT_VERSION,
    EVIDENCE_LEDGER_SCHEMA_VERSION,
    LEGACY_COMBINED_OVERSEG_RULE,
    SPLIT_FRAGMENTATION_RULE_IDS,
    MorphologyCandidateResult,
)
from ionogram_morphology_lab.utils.paths import ensure_dir

CACHE_FORMAT = "iml-morph-candidate-cache-v2"

MISS_NO_INDEX = "no_index"
MISS_KEY_MISMATCH = "key_mismatch"
MISS_RULESET_CHANGED = "ruleset_changed"
MISS_DIAGNOSTICS_IDENTITY = "diagnostics_identity_changed"
MISS_CORRUPT = "corrupt_result"
MISS_STALE = "stale_result"
MISS_TEMPORAL = "temporal_signature_changed"
MISS_INCOMPATIBLE_CACHE_SCHEMA = "incompatible_candidate_cache_schema"
MISS_INCOMPATIBLE_LEDGER_SCHEMA = "incompatible_ledger_schema"
MISS_MISSING_LEDGER_ENTRIES = "missing_required_ledger_entries"
MISS_SOURCE_IDENTITY = "source_identity_mismatch"
MISS_FRAME_IDENTITY = "frame_identity_mismatch"
MISS_HASH = "hash_mismatch"


@dataclass
class CandidateCacheCounters:
    candidate_cache_lookup_count: int = 0
    candidate_cache_hit_count: int = 0
    candidate_cache_miss_count: int = 0
    candidate_engine_evaluation_count: int = 0
    v2_request_count: int = 0
    candidate_loaded_on_frame_activation_count: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "candidate_cache_lookup_count": self.candidate_cache_lookup_count,
            "candidate_cache_hit_count": self.candidate_cache_hit_count,
            "candidate_cache_miss_count": self.candidate_cache_miss_count,
            "candidate_engine_evaluation_count": self.candidate_engine_evaluation_count,
            "v2_request_count": self.v2_request_count,
            "candidate_loaded_on_frame_activation_count": self.candidate_loaded_on_frame_activation_count,
        }

    def reset(self) -> None:
        self.candidate_cache_lookup_count = 0
        self.candidate_cache_hit_count = 0
        self.candidate_cache_miss_count = 0
        self.candidate_engine_evaluation_count = 0
        self.v2_request_count = 0
        self.candidate_loaded_on_frame_activation_count = 0


@dataclass(frozen=True)
class MorphologyCandidateCacheKey:
    source_sha256: str
    frame_index: int
    profile_id: str
    signal_contract_id: str
    feature_version: str
    diagnostics_cache_id: str
    candidate_engine_version: str
    ruleset_version: str
    ruleset_hash: str
    temporal_context_signature: str = ""
    candidate_cache_schema_version: int = CANDIDATE_CACHE_SCHEMA_VERSION
    evidence_ledger_schema_version: int = EVIDENCE_LEDGER_SCHEMA_VERSION
    candidate_result_contract_version: int = CANDIDATE_RESULT_CONTRACT_VERSION

    def digest(self) -> str:
        payload = "|".join(
            [
                self.source_sha256,
                str(int(self.frame_index)),
                self.profile_id,
                self.signal_contract_id,
                self.feature_version,
                self.diagnostics_cache_id,
                self.candidate_engine_version,
                self.ruleset_version,
                self.ruleset_hash,
                self.temporal_context_signature,
                str(int(self.candidate_cache_schema_version)),
                str(int(self.evidence_ledger_schema_version)),
                str(int(self.candidate_result_contract_version)),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_sha256": self.source_sha256,
            "frame_index": int(self.frame_index),
            "profile_id": self.profile_id,
            "signal_contract_id": self.signal_contract_id,
            "feature_version": self.feature_version,
            "diagnostics_cache_id": self.diagnostics_cache_id,
            "candidate_engine_version": self.candidate_engine_version,
            "ruleset_version": self.ruleset_version,
            "ruleset_hash": self.ruleset_hash,
            "temporal_context_signature": self.temporal_context_signature,
            "candidate_cache_schema_version": int(self.candidate_cache_schema_version),
            "evidence_ledger_schema_version": int(self.evidence_ledger_schema_version),
            "candidate_result_contract_version": int(self.candidate_result_contract_version),
            "digest": self.digest(),
        }


def make_candidate_cache_key(
    *,
    source_sha256: str,
    frame_index: int,
    profile_id: str,
    signal_contract_id: str,
    feature_version: str,
    diagnostics_cache_id: str,
    ruleset_version: str,
    ruleset_hash: str,
    temporal_context_signature: str = "",
    candidate_engine_version: str = CANDIDATE_ENGINE_VERSION,
    candidate_cache_schema_version: int = CANDIDATE_CACHE_SCHEMA_VERSION,
    evidence_ledger_schema_version: int = EVIDENCE_LEDGER_SCHEMA_VERSION,
    candidate_result_contract_version: int = CANDIDATE_RESULT_CONTRACT_VERSION,
) -> MorphologyCandidateCacheKey:
    return MorphologyCandidateCacheKey(
        source_sha256=source_sha256,
        frame_index=int(frame_index),
        profile_id=str(profile_id or ""),
        signal_contract_id=str(signal_contract_id or ""),
        feature_version=feature_version,
        diagnostics_cache_id=diagnostics_cache_id,
        candidate_engine_version=candidate_engine_version,
        ruleset_version=ruleset_version,
        ruleset_hash=ruleset_hash,
        temporal_context_signature=temporal_context_signature or "",
        candidate_cache_schema_version=int(candidate_cache_schema_version),
        evidence_ledger_schema_version=int(evidence_ledger_schema_version),
        candidate_result_contract_version=int(candidate_result_contract_version),
    )


@dataclass
class CandidateCacheLookup:
    hit: bool
    result: dict[str, Any] | None = None
    miss_reason: str | None = None
    key_digest: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


def _ledger_rule_ids(payload: dict[str, Any]) -> set[str]:
    return {
        str(e.get("rule_id") or "")
        for e in (payload.get("evidence_ledger") or [])
        if isinstance(e, dict)
    }


def validate_candidate_cache_payload(
    payload: dict[str, Any],
    key: MorphologyCandidateCacheKey,
    *,
    meta: dict[str, Any] | None = None,
) -> str | None:
    """Return miss reason if payload is incompatible; None if acceptable."""
    meta = meta or {}
    fmt = str(meta.get("cache_format") or payload.get("cache_format") or "")
    cache_schema = int(
        meta.get("candidate_cache_schema_version")
        or payload.get("candidate_cache_schema_version")
        or (1 if "v1" in fmt or fmt.endswith("-v1") or not fmt else 0)
    )
    if cache_schema != int(key.candidate_cache_schema_version) or fmt not in {"", CACHE_FORMAT}:
        # Accept missing format only when schema version matches current
        if cache_schema != int(key.candidate_cache_schema_version):
            return MISS_INCOMPATIBLE_CACHE_SCHEMA
        if fmt and fmt != CACHE_FORMAT:
            return MISS_INCOMPATIBLE_CACHE_SCHEMA

    ledger_schema = int(
        payload.get("evidence_ledger_schema_version")
        or meta.get("evidence_ledger_schema_version")
        or 0
    )
    if ledger_schema != int(key.evidence_ledger_schema_version):
        return MISS_INCOMPATIBLE_LEDGER_SCHEMA

    contract = int(
        payload.get("candidate_result_contract_version")
        or meta.get("candidate_result_contract_version")
        or 0
    )
    if contract != int(key.candidate_result_contract_version):
        return MISS_INCOMPATIBLE_CACHE_SCHEMA

    if str(payload.get("source_sha256") or "") != key.source_sha256:
        return MISS_SOURCE_IDENTITY
    if int(payload.get("frame_index") or -1) != int(key.frame_index):
        return MISS_FRAME_IDENTITY
    if str(payload.get("diagnostics_cache_id") or "") != key.diagnostics_cache_id:
        return MISS_DIAGNOSTICS_IDENTITY

    if not isinstance(payload, dict) or "candidate" not in payload:
        return MISS_CORRUPT

    rule_ids = _ledger_rule_ids(payload)
    if LEGACY_COMBINED_OVERSEG_RULE in rule_ids:
        return MISS_INCOMPATIBLE_LEDGER_SCHEMA
    # Fragmentation / overseg abstention path must carry split rows when those reasons fire
    reasons = set(payload.get("abstention_reasons") or [])
    frag_reasons = {
        "oversegmentation_suspected",
        "severe_fragmentation",
        "both_oversegmentation_and_fragmentation",
        "oversegmentation_or_severe_fragmentation",
    }
    if reasons & frag_reasons:
        if not SPLIT_FRAGMENTATION_RULE_IDS.issubset(rule_ids):
            return MISS_MISSING_LEDGER_ENTRIES

    stored_rh = str(payload.get("result_hash") or meta.get("result_hash") or "")
    if stored_rh and meta.get("result_hash") and str(meta.get("result_hash")) != stored_rh:
        return MISS_HASH

    ledger = payload.get("evidence_ledger") or []
    if ledger:
        # Prefer explicit ledger hash when present; otherwise recompute for integrity
        expected_lh = payload.get("evidence_ledger_hash")
        if expected_lh and str(expected_lh) != ledger_hash(ledger):
            return MISS_HASH

    return None


def incompatible_candidate_cache_message(lang: str) -> str:
    if lang == "ru":
        return (
            "Кэш кандидата создан предыдущей версией. Пересчитайте только "
            "кандидата; пересчёт V2 не требуется."
        )
    return (
        "Candidate cache was created by a previous version. Recalculate the "
        "candidate only; V2 recalculation is not required."
    )


def _legacy_v1_digest(key: MorphologyCandidateCacheKey) -> str:
    """Digest used by iml-morph-candidate-cache-v1 (no schema fields in key)."""
    payload = "|".join(
        [
            key.source_sha256,
            str(int(key.frame_index)),
            key.profile_id,
            key.signal_contract_id,
            key.feature_version,
            key.diagnostics_cache_id,
            # Prior engine version often paired with v1 cache
            "iml-morph-candidate-0.1.0",
            key.ruleset_version,
            key.ruleset_hash,
            key.temporal_context_signature or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class MorphologyCandidateCache:
    """Filesystem cache under ``{cache_root}/morphology_candidates/{digest[:24]}/``."""

    def __init__(self, cache_root: Path | str):
        self.root = Path(cache_root) / "morphology_candidates"
        ensure_dir(self.root)
        self.counters = CandidateCacheCounters()

    def _dir(self, key: MorphologyCandidateCacheKey) -> Path:
        return self.root / key.digest()[:24]

    def _probe_legacy_incompatible(self, key: MorphologyCandidateCacheKey) -> CandidateCacheLookup | None:
        """If a v1 cache entry exists for this identity, return incompatible miss (not a hit)."""
        legacy_digest = _legacy_v1_digest(key)
        d = self.root / legacy_digest[:24]
        meta_path = d / "meta.json"
        result_path = d / "result.json"
        if not meta_path.is_file() or not result_path.is_file():
            # Also try current engine version with v1 digest shape (schema omitted)
            payload = "|".join(
                [
                    key.source_sha256,
                    str(int(key.frame_index)),
                    key.profile_id,
                    key.signal_contract_id,
                    key.feature_version,
                    key.diagnostics_cache_id,
                    key.candidate_engine_version,
                    key.ruleset_version,
                    key.ruleset_hash,
                    key.temporal_context_signature or "",
                ]
            )
            alt = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            d = self.root / alt[:24]
            meta_path = d / "meta.json"
            result_path = d / "result.json"
            if not meta_path.is_file() or not result_path.is_file():
                return None
            legacy_digest = alt
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return CandidateCacheLookup(
                False, miss_reason=MISS_CORRUPT, key_digest=legacy_digest
            )
        # Treat any readable legacy entry for this identity as schema-incompatible
        if meta.get("cache_format") == CACHE_FORMAT and int(
            meta.get("candidate_cache_schema_version") or 0
        ) == CANDIDATE_CACHE_SCHEMA_VERSION:
            return None
        rule_ids = _ledger_rule_ids(payload if isinstance(payload, dict) else {})
        if (
            meta.get("cache_format") == "iml-morph-candidate-cache-v1"
            or LEGACY_COMBINED_OVERSEG_RULE in rule_ids
            or int(meta.get("candidate_cache_schema_version") or 0) < CANDIDATE_CACHE_SCHEMA_VERSION
        ):
            return CandidateCacheLookup(
                False,
                miss_reason=MISS_INCOMPATIBLE_CACHE_SCHEMA,
                key_digest=legacy_digest,
                meta=meta if isinstance(meta, dict) else {},
            )
        return None

    def lookup(self, key: MorphologyCandidateCacheKey) -> CandidateCacheLookup:
        """Exact-key lookup with schema/content validation. Bare dir ≠ hit."""
        self.counters.candidate_cache_lookup_count += 1
        digest = key.digest()
        d = self._dir(key)
        meta_path = d / "meta.json"
        result_path = d / "result.json"
        if not d.is_dir():
            legacy = self._probe_legacy_incompatible(key)
            if legacy is not None:
                self.counters.candidate_cache_miss_count += 1
                return legacy
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_NO_INDEX, key_digest=digest)
        if not meta_path.is_file() or not result_path.is_file():
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_CORRUPT, key_digest=digest)
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_CORRUPT, key_digest=digest)

        # Detect legacy v1 format early (even if digest folder somehow matches)
        if meta.get("cache_format") in {"iml-morph-candidate-cache-v1", None} and int(
            meta.get("candidate_cache_schema_version") or 0
        ) < CANDIDATE_CACHE_SCHEMA_VERSION:
            # Also scan sibling legacy dirs by walking is expensive; key digest now includes schema
            # so v1 entries live under different digests — still reject if somehow present.
            if meta.get("cache_format") == "iml-morph-candidate-cache-v1" or int(
                meta.get("candidate_cache_schema_version") or 0
            ) != CANDIDATE_CACHE_SCHEMA_VERSION:
                self.counters.candidate_cache_miss_count += 1
                return CandidateCacheLookup(
                    False, miss_reason=MISS_INCOMPATIBLE_CACHE_SCHEMA, key_digest=digest, meta=meta
                )

        if meta.get("cache_format") != CACHE_FORMAT:
            self.counters.candidate_cache_miss_count += 1
            reason = (
                MISS_INCOMPATIBLE_CACHE_SCHEMA
                if "morph-candidate-cache" in str(meta.get("cache_format") or "")
                else MISS_STALE
            )
            return CandidateCacheLookup(False, miss_reason=reason, key_digest=digest, meta=meta)
        if meta.get("digest") != digest:
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_KEY_MISMATCH, key_digest=digest, meta=meta)

        stored_key = meta.get("key") or {}
        if stored_key.get("diagnostics_cache_id") != key.diagnostics_cache_id:
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(
                False, miss_reason=MISS_DIAGNOSTICS_IDENTITY, key_digest=digest, meta=meta
            )
        if meta.get("ruleset_hash") != key.ruleset_hash or stored_key.get("ruleset_hash") != key.ruleset_hash:
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_RULESET_CHANGED, key_digest=digest, meta=meta)
        if meta.get("candidate_engine_version") != key.candidate_engine_version:
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_STALE, key_digest=digest, meta=meta)
        if (stored_key.get("temporal_context_signature") or "") != (key.temporal_context_signature or ""):
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=MISS_TEMPORAL, key_digest=digest, meta=meta)

        content_miss = validate_candidate_cache_payload(payload, key, meta=meta)
        if content_miss:
            self.counters.candidate_cache_miss_count += 1
            return CandidateCacheLookup(False, miss_reason=content_miss, key_digest=digest, meta=meta)

        self.counters.candidate_cache_hit_count += 1
        return CandidateCacheLookup(True, result=payload, key_digest=digest, meta=meta)

    def get(self, key: MorphologyCandidateCacheKey) -> dict[str, Any] | None:
        lu = self.lookup(key)
        return lu.result if lu.hit else None

    def put(self, key: MorphologyCandidateCacheKey, result: MorphologyCandidateResult | dict[str, Any]) -> Path:
        d = self._dir(key)
        ensure_dir(d)
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        payload.setdefault("candidate_cache_schema_version", key.candidate_cache_schema_version)
        payload.setdefault("evidence_ledger_schema_version", key.evidence_ledger_schema_version)
        payload.setdefault("candidate_result_contract_version", key.candidate_result_contract_version)
        ledger = payload.get("evidence_ledger") or []
        payload["evidence_ledger_hash"] = ledger_hash(ledger)
        meta = {
            "cache_format": CACHE_FORMAT,
            "digest": key.digest(),
            "key": key.to_dict(),
            "ruleset_hash": key.ruleset_hash,
            "candidate_engine_version": key.candidate_engine_version,
            "candidate_cache_schema_version": key.candidate_cache_schema_version,
            "evidence_ledger_schema_version": key.evidence_ledger_schema_version,
            "candidate_result_contract_version": key.candidate_result_contract_version,
            "result_hash": payload.get("result_hash"),
            "evidence_ledger_hash": payload.get("evidence_ledger_hash"),
        }
        (d / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        (d / "result.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        return d

    def clear_frame(self, key: MorphologyCandidateCacheKey) -> bool:
        d = self._dir(key)
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            return True
        return False

    def clear_all(self) -> None:
        if self.root.is_dir():
            shutil.rmtree(self.root, ignore_errors=True)
            ensure_dir(self.root)


def result_from_dict(d: dict[str, Any]) -> MorphologyCandidateResult:
    from ionogram_morphology_lab.morphology_candidate.types import (
        AxisEvidenceSummary,
        EvidenceLedgerEntry,
        InterferenceAssessment,
    )

    h = d.get("h_evidence") or {}
    v = d.get("v_evidence") or {}
    inter = d.get("interference") or {}
    ledger_entries = []
    for e in d.get("evidence_ledger") or []:
        if not isinstance(e, dict):
            continue
        known = set(EvidenceLedgerEntry.__dataclass_fields__.keys())
        filtered = {k: val for k, val in e.items() if k in known}
        ledger_entries.append(EvidenceLedgerEntry(**filtered))
    ledger = tuple(ledger_entries)
    interference = InterferenceAssessment(
        level=str(inter.get("level") or "none"),
        vertical_interference=bool(inter.get("vertical_interference")),
        horizontal_interference=bool(inter.get("horizontal_interference")),
        floor_clutter=bool(inter.get("floor_clutter")),
        impulsive_noise=bool(inter.get("impulsive_noise")),
        broad_artifact=bool(inter.get("broad_artifact")),
        secondary_multiple_echo_suspicion=bool(inter.get("secondary_multiple_echo_suspicion")),
        oversegmentation=bool(inter.get("oversegmentation")),
        missing_data_regions=bool(inter.get("missing_data_regions")),
        raw_v2_interference_level=str(inter.get("raw_v2_interference_level") or ""),
        notes=tuple(inter.get("notes") or ()),
    )
    return MorphologyCandidateResult(
        candidate=d["candidate"],
        candidate_engine_version=d["candidate_engine_version"],
        ruleset_id=d["ruleset_id"],
        ruleset_version=d["ruleset_version"],
        ruleset_hash=d["ruleset_hash"],
        feature_version=d["feature_version"],
        source_sha256=d["source_sha256"],
        frame_index=int(d["frame_index"]),
        interpreted_time=d.get("interpreted_time") or "",
        diagnostics_cache_id=d["diagnostics_cache_id"],
        input_identity_hash=d["input_identity_hash"],
        assessability=d["assessability"],
        abstained=bool(d["abstained"]),
        abstention_reasons=tuple(d.get("abstention_reasons") or ()),
        evidence_strength=d["evidence_strength"],
        h_evidence=AxisEvidenceSummary(
            supported=bool(h.get("supported")),
            strength=str(h.get("strength") or "none"),
            primary_features=tuple(h.get("primary_features") or ()),
            notes=tuple(h.get("notes") or ()),
        ),
        v_evidence=AxisEvidenceSummary(
            supported=bool(v.get("supported")),
            strength=str(v.get("strength") or "none"),
            primary_features=tuple(v.get("primary_features") or ()),
            notes=tuple(v.get("notes") or ()),
        ),
        coexistence_summary=d.get("coexistence_summary") or {},
        interference=interference,
        quality_summary=d.get("quality_summary") or {},
        ambiguity_summary=d.get("ambiguity_summary") or {},
        temporal_summary=d.get("temporal_summary") or {},
        evidence_ledger=ledger,
        warnings=tuple(d.get("warnings") or ()),
        provisional=bool(d.get("provisional", True)),
        shadow_mode=bool(d.get("shadow_mode", True)),
        scientifically_validated=bool(d.get("scientifically_validated", False)),
        production_applied=bool(d.get("production_applied", False)),
        created_at=d.get("created_at") or "",
        human_explanation_en=d.get("human_explanation_en") or "",
        human_explanation_ru=d.get("human_explanation_ru") or "",
        result_hash=d.get("result_hash") or "",
        candidate_cache_schema_version=int(
            d.get("candidate_cache_schema_version") or CANDIDATE_CACHE_SCHEMA_VERSION
        ),
        evidence_ledger_schema_version=int(
            d.get("evidence_ledger_schema_version") or EVIDENCE_LEDGER_SCHEMA_VERSION
        ),
        candidate_result_contract_version=int(
            d.get("candidate_result_contract_version") or CANDIDATE_RESULT_CONTRACT_VERSION
        ),
    )

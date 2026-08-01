from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ionogram_morphology_lab.app.settings_store import SettingsStore, DEFAULT_SETTINGS
from ionogram_morphology_lab.cache.frame_store import FrameStore, LRUFrameCache
from ionogram_morphology_lab.help.content import HELP_SECTIONS, help_section_ids, search_help
from ionogram_morphology_lab.i18n import I18n
from ionogram_morphology_lab.instrument_profiles.schema import load_profile
from ionogram_morphology_lab.projects.batch_selection import (
    DEFAULT_KFU_INTERVAL_MINUTES,
    select_custom_list,
    select_frame_range,
    select_full_day,
    select_single,
    select_time_range,
)
from ionogram_morphology_lab.projects.time_mapping import (
    format_hhmm,
    frame_to_minute,
    minute_to_frame,
    parse_hhmm,
)
from ionogram_morphology_lab.security import (
    ForbiddenPathError,
    ProtectedStudyConfig,
    default_blocklist,
    reset_protection,
    set_active_protection,
)
from ionogram_morphology_lab.synthetic.generator import write_synthetic_mat_library
from ionogram_morphology_lab.ui.presenters import confidence_explanation, explain_result
from ionogram_morphology_lab.ui.session import AppSession
from ionogram_morphology_lab.utils.hashing import sha256_file
from ionogram_morphology_lab.utils.paths import app_root


@pytest.fixture
def syn_profile_mat(tmp_path):
    syn = tmp_path / "syn"
    write_synthetic_mat_library(syn)
    path = syn / "demo_horizontally_diffuse.mat"
    profile = {
        "profile_id": "syn_test_profile",
        "amplitude_variable_name": "Amp_all",
        "height_bins": 256,
        "frequency_bins": 400,
        "frames_per_file": 3,
        "matrix_layout": "frames_stacked_rows",
        "profile_verification_status": "user-defined-unverified",
        "time_mapping": "matlab_index_minus_1_minute",
    }
    return path, profile


def test_time_index_sync():
    assert frame_to_minute(1) == 0
    assert format_hhmm(0) == "00:00"
    assert format_hhmm(frame_to_minute(1440)) == "23:59"
    assert minute_to_frame(0) == 1
    assert parse_hhmm("05:10") == 5 * 60 + 10


def test_batch_selection_modes_and_121_explanation():
    assert select_single(10).expected_count == 1
    r = select_frame_range(1, 1440, 121)
    assert r.expected_count == 12
    assert "121" in r.explanation_en
    assert "121" in r.explanation_ru
    assert DEFAULT_KFU_INTERVAL_MINUTES == 10
    day = select_full_day(10)
    assert day.expected_count == 144
    tr = select_time_range("05:00", "09:00", 10)
    assert tr.expected_count == 25
    custom = select_custom_list(["1", "05:10", "100"])
    assert custom.expected_count == 3


def test_frame_store_cache_lru_prefetch(syn_profile_mat, tmp_path):
    path, profile = syn_profile_mat
    before = sha256_file(path)
    store = FrameStore(path, profile, cache_root=tmp_path / "cache", prefetch_radius=2, lru_capacity=4)
    st = store.build_cache()
    assert st.valid
    f1 = store.get_frame(1)
    f2 = store.get_frame(2)
    assert f1.shape == (256, 400)
    assert not np.shares_memory(f1, f2)
    # second access hits LRU
    hits0 = store.stats["cache_hits"]
    _ = store.get_frame(1)
    assert store.stats["cache_hits"] > hits0
    # identity mismatch rejects reuse
    bad = FrameStore(
        path,
        {**profile, "profile_id": "other"},
        cache_root=tmp_path / "cache",
    )
    # different identity dir
    assert bad.identity.key() != store.identity.key()
    store.delete_cache()
    assert not store.status().valid
    assert sha256_file(path) == before


def test_session_prefers_real_import(syn_profile_mat, tmp_path):
    path, profile = syn_profile_mat
    settings = SettingsStore(tmp_path / "settings.json")
    session = AppSession(settings=settings)
    session.profile = profile
    session.profile_id = profile["profile_id"]
    session.set_active_mat(path)
    assert session.has_real_import()
    store = session.ensure_store()
    store.build_cache()
    assert store.get_frame(1).shape == (256, 400)


def test_null_confidence_explained():
    rec = {"confidence_score": None, "final_auto_status": "proposed", "candidate_morphology": "mixed", "measured_features": {}}
    en = confidence_explanation(rec, "en")
    ru = confidence_explanation(rec, "ru")
    assert "calibration" in en.lower()
    assert "калибров" in ru.lower()
    assert "null" not in explain_result(rec, "en").split("\n")[0].lower() or "No numerical" in explain_result(rec, "en")


def test_help_sections_and_i18n_parity():
    assert len(help_section_ids()) >= 54
    assert len(HELP_SECTIONS) >= 54
    en = I18n("en")
    ru = I18n("ru")
    assert set(en.keys()) == set(ru.keys())
    assert len(en.keys()) >= 140
    assert search_help("cache", "en")


def test_settings_analysis_mode_defaults_to_strict_and_user_choice_persists(tmp_path):
    s = SettingsStore(tmp_path / "s.json")
    assert s.get("analysis", "mode") == "scientific_strict"
    s.set("analysis", "mode", "standard")
    s.save()
    s2 = SettingsStore(tmp_path / "s.json")
    assert s2.get("analysis", "mode") == "standard"
    assert DEFAULT_SETTINGS["analysis"]["mode"] == "scientific_strict"


def test_optional_protection_blocks_only_when_enabled():
    path = r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\11_rendered_frames\x.png"
    reset_protection()
    assert default_blocklist().assert_allowed(path)
    set_active_protection(
        ProtectedStudyConfig(enabled=True, protected_path_fragments=["11_rendered_frames"])
    )
    with pytest.raises(ForbiddenPathError):
        default_blocklist().assert_allowed(path)
    reset_protection()


def test_no_dawn_dusk_in_batch_selection_module():
    import ionogram_morphology_lab.projects.batch_selection as bs
    src = Path(bs.__file__).read_text(encoding="utf-8").lower()
    assert "dawn" not in src and "dusk" not in src and "solar" not in src

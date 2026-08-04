"""Sequence-to-morphology UI state for the currently displayed frame (Phase 4C.1e / 4C.1e.1).

UI/UX clarity only — does not change V2 or candidate scientific contracts.
No Qt imports; safe at module import time.
"""

from __future__ import annotations

from typing import Any, Mapping

# Bump when the state ID set or presentation contract changes (Build Identity).
SEQUENCE_STATE_CONTRACT_VERSION = 1

# Diagnostics layout schema (Layers | Canvas | Inspector defaults). Owned here so
# Build Identity and the page share one constant without circular imports.
FD_LAYOUT_SCHEMA_VERSION = 2

# Explicit states for the currently displayed frame during / after sequence work.
SEQUENCE_FRAME_STATES = (
    "sequence_not_started",
    "sequence_v2_pending",
    "sequence_v2_running_current_frame",
    "sequence_v2_ready_candidate_pending",
    "sequence_candidate_running",
    "sequence_candidate_ready",
    "sequence_candidate_cached",
    "sequence_frame_not_yet_processed",
    "sequence_frame_failed",
    "sequence_cancelled",
    "sequence_result_stale",
)

_MESSAGES: dict[str, dict[str, str]] = {
    "sequence_not_started": {
        "ru": "Последовательность ещё не запущена для текущего кадра.",
        "en": "Sequence has not been started for the current frame.",
    },
    "sequence_v2_pending": {
        "ru": (
            "Последовательность обрабатывается. V2 для текущего кадра ещё не "
            "завершён. Предварительный кандидат станет доступен после появления "
            "совместимого результата V2."
        ),
        "en": (
            "Sequence is processing. V2 for the current frame is not finished yet. "
            "The provisional candidate becomes available after a compatible V2 result appears."
        ),
    },
    "sequence_v2_running_current_frame": {
        "ru": (
            "Последовательность обрабатывается. Сейчас выполняется V2 для текущего кадра. "
            "Предварительный кандидат станет доступен после появления совместимого результата V2."
        ),
        "en": (
            "Sequence is processing. V2 is running for the current frame. "
            "The provisional candidate becomes available after a compatible V2 result appears."
        ),
    },
    "sequence_v2_ready_candidate_pending": {
        "ru": (
            "V2 для текущего кадра готов. Предварительный кандидат морфологии "
            "ещё не рассчитан — можно запустить расчёт кандидата."
        ),
        "en": (
            "V2 for the current frame is ready. The provisional morphology candidate "
            "is not calculated yet — you can run Calculate candidate."
        ),
    },
    "sequence_candidate_running": {
        "ru": (
            "V2 для текущего кадра готов. Выполняется расчёт предварительного "
            "кандидата морфологии."
        ),
        "en": (
            "V2 for the current frame is ready. Provisional morphology candidate "
            "calculation is in progress."
        ),
    },
    "sequence_candidate_ready": {
        "ru": "V2 и предварительный кандидат для текущего кадра готовы.",
        "en": "V2 and the provisional candidate for the current frame are ready.",
    },
    "sequence_candidate_cached": {
        "ru": (
            "V2 и предварительный кандидат загружены из кэша.\n"
            "Расчёт не выполнялся."
        ),
        "en": (
            "V2 and the provisional candidate were loaded from cache.\n"
            "No calculation was performed."
        ),
    },
    "sequence_frame_not_yet_processed": {
        "ru": "Текущий кадр ещё не обработан в этой последовательности.",
        "en": "The current frame has not been processed in this sequence yet.",
    },
    "sequence_frame_failed": {
        "ru": "Обработка текущего кадра в последовательности завершилась ошибкой.",
        "en": "Sequence processing failed for the current frame.",
    },
    "sequence_cancelled": {
        "ru": "Последовательность отменена. Результат для текущего кадра может быть неполным.",
        "en": "Sequence was cancelled. The current frame result may be incomplete.",
    },
    "sequence_result_stale": {
        "ru": "Результат последовательности устарел относительно текущего источника или поколения.",
        "en": "Sequence result is stale relative to the current source or generation.",
    },
}

# Explicit enablement + severity for every canonical state (no silent fall-through).
_CONTROLS: dict[str, dict[str, Any]] = {
    "sequence_not_started": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "info",
    },
    "sequence_v2_pending": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "busy",
    },
    "sequence_v2_running_current_frame": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "busy",
    },
    "sequence_v2_ready_candidate_pending": {
        "calc_enabled": True,
        "recalc_enabled": True,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_ready",
        "severity": "ready",
    },
    "sequence_candidate_running": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "candidate_running",
        "severity": "busy",
    },
    "sequence_candidate_ready": {
        "calc_enabled": False,
        "recalc_enabled": True,
        "evidence_enabled": True,
        "review_enabled": True,
        "calc_tooltip_key": "has_candidate",
        "severity": "ok",
    },
    "sequence_candidate_cached": {
        "calc_enabled": False,
        "recalc_enabled": True,
        "evidence_enabled": True,
        "review_enabled": True,
        "calc_tooltip_key": "has_candidate",
        "severity": "ok",
    },
    "sequence_frame_not_yet_processed": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "busy",
    },
    "sequence_frame_failed": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "error",
    },
    "sequence_cancelled": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "warn",
    },
    "sequence_result_stale": {
        "calc_enabled": False,
        "recalc_enabled": False,
        "evidence_enabled": False,
        "review_enabled": False,
        "calc_tooltip_key": "v2_not_ready",
        "severity": "warn",
    },
}


def assert_sequence_state_catalog_complete() -> None:
    """Raise AssertionError if any state lacks message or control contract."""
    for state in SEQUENCE_FRAME_STATES:
        if state not in _MESSAGES:
            raise AssertionError(f"missing RU/EN message for {state}")
        for lang in ("ru", "en"):
            text = (_MESSAGES[state].get(lang) or "").strip()
            if not text:
                raise AssertionError(f"empty {lang} message for {state}")
            if text == state or text.startswith("sequence_"):
                raise AssertionError(f"raw state id leaked as {lang} text for {state}")
        if state not in _CONTROLS:
            raise AssertionError(f"missing control contract for {state}")


# Validate catalog at import (deterministic; no I/O).
assert_sequence_state_catalog_complete()


def sequence_state_message(state: str, lang: str) -> str:
    """Localized explanation for a sequence frame state."""
    key = "ru" if lang == "ru" else "en"
    if state not in _MESSAGES:
        # Never return an untranslated raw id.
        return _MESSAGES["sequence_not_started"][key]
    return _MESSAGES[state][key]


def resolve_sequence_frame_state(
    *,
    sequence_mode: bool,
    running: bool,
    job_state: str,
    generation_id: str,
    active_generation_id: str,
    current_frame: int,
    sequence_frames: list[int] | tuple[int, ...] | None,
    sequence_results: list[Mapping[str, Any]] | None,
    progress_frame: int | None,
    v2_ready: bool,
    candidate_present: bool,
    candidate_cached: bool,
    candidate_running: bool,
    cancelled: bool,
) -> str:
    """Derive the UI state for the currently displayed frame.

    Identity: callers must pass only results belonging to ``active_generation_id`` /
    current source. This function does not open MAT or run science.
    """
    if not sequence_mode:
        return "sequence_not_started"

    if generation_id and active_generation_id and generation_id != active_generation_id:
        return "sequence_result_stale"

    if cancelled or job_state == "cancelled":
        row = _row_for_frame(sequence_results, current_frame)
        if row is None and not v2_ready:
            return "sequence_cancelled"
        if row is not None and str(row.get("status") or "") == "failed":
            return "sequence_frame_failed"
        if candidate_present:
            return "sequence_candidate_cached" if candidate_cached else "sequence_candidate_ready"
        if v2_ready:
            return "sequence_v2_ready_candidate_pending"
        return "sequence_cancelled"

    frames = list(sequence_frames or [])
    row = _row_for_frame(sequence_results, current_frame)
    in_selection = (not frames) or (int(current_frame) in {int(f) for f in frames})

    if running:
        if progress_frame is not None and int(progress_frame) == int(current_frame):
            if not v2_ready and row is None:
                return "sequence_v2_running_current_frame"
        if row is None and in_selection and not v2_ready:
            return (
                "sequence_frame_not_yet_processed"
                if _frame_after_progress(frames, current_frame, progress_frame)
                else "sequence_v2_pending"
            )
        if row is not None and str(row.get("status") or "") == "failed":
            return "sequence_frame_failed"
        if v2_ready and candidate_running:
            return "sequence_candidate_running"
        if v2_ready and not candidate_present:
            return "sequence_v2_ready_candidate_pending"
        if candidate_present:
            return "sequence_candidate_cached" if candidate_cached else "sequence_candidate_ready"
        return "sequence_v2_pending"

    # Idle / completed
    if row is None and not v2_ready:
        if frames and int(current_frame) not in {int(f) for f in frames}:
            return "sequence_not_started"
        if sequence_results:
            return "sequence_frame_not_yet_processed"
        return "sequence_not_started"

    if row is not None and str(row.get("status") or "") == "failed":
        return "sequence_frame_failed"

    if candidate_running:
        return "sequence_candidate_running"

    if candidate_present:
        return "sequence_candidate_cached" if candidate_cached else "sequence_candidate_ready"

    if v2_ready:
        return "sequence_v2_ready_candidate_pending"

    return "sequence_v2_pending"


def _row_for_frame(
    results: list[Mapping[str, Any]] | None, frame: int
) -> Mapping[str, Any] | None:
    if not results:
        return None
    for r in results:
        try:
            if int(r.get("frame_index", -1)) == int(frame):
                return r
        except (TypeError, ValueError):
            continue
    return None


def _frame_after_progress(
    frames: list[int], current_frame: int, progress_frame: int | None
) -> bool:
    """True when current frame appears later in the sequence than the progress frame."""
    if progress_frame is None or not frames:
        return False
    try:
        ci = frames.index(int(current_frame))
        pi = frames.index(int(progress_frame))
    except ValueError:
        return False
    return ci > pi


def candidate_controls_for_state(state: str) -> dict[str, Any]:
    """Return enablement flags and tooltip keys for morph actions."""
    if state in _CONTROLS:
        return dict(_CONTROLS[state])
    # Safe fallback — never an untranslated hole.
    return dict(_CONTROLS["sequence_not_started"])


def control_tooltip(tooltip_key: str, lang: str) -> str:
    ru = lang == "ru"
    mapping = {
        "v2_not_ready": (
            "V2 для текущего кадра ещё не готов."
            if ru
            else "V2 for the current frame is not ready yet."
        ),
        "v2_ready": (
            "Совместимый V2 готов — можно рассчитать кандидата."
            if ru
            else "Compatible V2 is ready — you can calculate the candidate."
        ),
        "candidate_running": (
            "Расчёт кандидата уже выполняется."
            if ru
            else "Candidate calculation is already in progress."
        ),
        "has_candidate": (
            "Кандидат уже есть — используйте пересчёт при необходимости."
            if ru
            else "Candidate already exists — use recalculate if needed."
        ),
        "default": "",
    }
    return mapping.get(tooltip_key, "")


DIAGNOSTICS_SHORTCUTS: tuple[tuple[str, str, str], ...] = (
    (
        "Ctrl+0",
        "Сбросить расположение Diagnostics",
        "Reset Diagnostics layout",
    ),
    (
        "Ctrl+Shift+F",
        "Открыть таблицу признаков отдельно",
        "Open Features table in a separate window",
    ),
    (
        "Ctrl+Shift+R",
        "Открыть результаты последовательности отдельно",
        "Open Sequence Results in a separate window",
    ),
    (
        "Escape",
        "Закрыть активное отдельное окно",
        "Close the active detached window",
    ),
)


def format_sequence_progress_status(
    *,
    lang: str,
    completed: int,
    total: int,
    progress_frame: int | None,
    last_completed_frame: int | None,
    running: bool,
    cancelled: bool,
    finished: bool,
) -> str:
    """Human sequence progress line (not a scientific worker-state dump)."""
    ru = lang == "ru"
    time_s = ""
    if progress_frame is not None:
        try:
            from ionogram_morphology_lab.projects.time_mapping import format_hhmm, frame_to_minute

            time_s = format_hhmm(frame_to_minute(int(progress_frame)))
        except Exception:
            time_s = ""
    if cancelled:
        return (
            f"Последовательность отменена: завершено {completed} из {total} кадров."
            if ru
            else f"Sequence cancelled: completed {completed} of {total} frames."
        )
    if finished or (not running and total > 0 and completed >= total):
        return (
            f"Последовательность завершена: {completed} из {total} кадров."
            if ru
            else f"Sequence complete: {completed} of {total} frames."
        )
    if running:
        if progress_frame is not None:
            t = f" ({time_s})" if time_s else ""
            return (
                f"Последовательность: обработано {completed} из {total} кадров. "
                f"Сейчас рассчитывается кадр {progress_frame}{t}."
                if ru
                else (
                    f"Sequence: processed {completed} of {total} frames. "
                    f"Now computing frame {progress_frame}{t}."
                )
            )
        return (
            f"Последовательность: обработано {completed} из {total} кадров."
            if ru
            else f"Sequence: processed {completed} of {total} frames."
        )
    if last_completed_frame is not None:
        return (
            f"Кадр {last_completed_frame} завершён. Признаки и кандидат загружены."
            if ru
            else f"Frame {last_completed_frame} completed. Features and candidate loaded."
        )
    return (
        f"Последовательность: {completed} из {total} кадров."
        if ru
        else f"Sequence: {completed} of {total} frames."
    )


def features_empty_message(
    kind: str,
    lang: str,
    *,
    frame: int | None = None,
) -> str:
    """Localized Features-tab empty-state copy (single active frame)."""
    ru = lang == "ru"
    if kind == "pending":
        return (
            "V2 для текущего кадра ещё не завершён. Признаки появятся после "
            "обработки этого кадра."
            if ru
            else "V2 for the current frame is not finished yet. Features will appear "
            "after this frame is processed."
        )
    if kind == "outside_sequence":
        fr = int(frame or 0)
        return (
            f"Кадр {fr} не входит в выбранную последовательность.\n"
            "Выберите строку результатов или включите «Следовать за обработкой»."
            if ru
            else f"Frame {fr} is not part of the selected sequence.\n"
            "Select a results row or enable “Follow processing”."
        )
    if kind == "hydrating":
        return (
            "Загрузка признаков текущего кадра…"
            if ru
            else "Loading features for the current frame…"
        )
    if kind == "failed":
        return (
            "Не удалось получить признаки для текущего кадра."
            if ru
            else "Could not obtain features for the current frame."
        )
    if kind == "not_applicable":
        return (
            "Для текущего кадра нет применимых научных признаков "
            "(нет пригодного следа или геометрия не даёт измеряемых величин)."
            if ru
            else "No applicable scientific features for the current frame "
            "(no usable trace, or geometry yields no measurable values)."
        )
    if kind == "no_result":
        return (
            "Нет результата V2 для текущего кадра."
            if ru
            else "No V2 result for the current frame."
        )
    return (
        "Нет признаков для отображения."
        if ru
        else "No features to display."
    )


def format_shortcuts_help(lang: str) -> str:
    """RU/EN shortcut + layout help for the Diagnostics Help drawer."""
    ru = lang == "ru"
    lines: list[str] = []
    lines.append("Быстрые команды" if ru else "Keyboard shortcuts")
    lines.append("")
    for key, ru_desc, en_desc in DIAGNOSTICS_SHORTCUTS:
        lines.append(f"{key} — {ru_desc if ru else en_desc}")
    lines.append("")
    if ru:
        lines.extend(
            [
                "Последовательность:",
                "— «Следовать за обработкой» автоматически показывает последний "
                "завершённый кадр.",
                "— Выбор строки приостанавливает автоматическое следование.",
                "— «Возобновить следование» возвращает переход к новым кадрам.",
                "— Подробные признаки отображаются только для выбранного кадра.",
                "",
                "Расположение:",
                "— Горизонтальный разделитель: Слои | Ионограмма | Инспектор.",
                "— В режиме последовательности вертикальный разделитель "
                "делит ионограмму и таблицу результатов.",
                "— Внешняя прокрутка страницы открывает нижние панели на низких экранах.",
                "",
                "Отдельные окна:",
                "— «Открыть таблицу отдельно» — таблица признаков в отдельном окне.",
                "— «Открыть результаты отдельно» — результаты последовательности.",
                "— «Следовать за кадром» обновляет окно при смене кадра.",
                "— «Закрепить на этом кадре» сохраняет привязку к выбранному кадру.",
                "— «Сбросить макет» (Ctrl+0) восстанавливает соотношение панелей, "
                "не очищая V2, кандидатов и кэш.",
            ]
        )
    else:
        lines.extend(
            [
                "Sequence:",
                "— “Follow processing” automatically shows the latest completed frame.",
                "— Selecting a row pauses automatic follow.",
                "— “Resume follow” returns to advancing with new frames.",
                "— Detailed Features are shown only for the selected frame.",
                "",
                "Layout:",
                "— Horizontal splitter: Layers | Ionogram | Inspector.",
                "— In Sequence mode a vertical splitter divides the ionogram and results table.",
                "— Outer page scrolling reaches lower panels on short displays.",
                "",
                "Detached windows:",
                "— “Open table in separate window” — Features in a resizable window.",
                "— “Open results in separate window” — Sequence Results.",
                "— “Follow current frame” updates the window when the frame changes.",
                "— “Pin to this frame” keeps the window bound to that frame identity.",
                "— “Reset layout” (Ctrl+0) restores pane ratios without clearing "
                "V2, candidates, or caches.",
            ]
        )
    return "\n".join(lines)

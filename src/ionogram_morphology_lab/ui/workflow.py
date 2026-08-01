"""Recommended user workflow derived from AppSession state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

StepStatus = Literal["completed", "incomplete", "warning", "blocked", "optional", "current"]


@dataclass
class WorkflowStep:
    step_id: str
    nav_key: str
    title_en: str
    title_ru: str
    status: StepStatus
    required: bool = True
    help_id: str = "quick_start"

    def title(self, lang: str) -> str:
        return self.title_ru if lang == "ru" else self.title_en


def _cache_ready(session: Any) -> bool:
    try:
        if not session.has_real_import():
            return False
        store = session.ensure_store()
        return bool(store.status().valid)
    except Exception:
        return False


def evaluate_workflow(session: Any) -> list[WorkflowStep]:
    """Return 11-step recommended path with statuses from current session."""
    has_project = session.project is not None
    has_data = bool(session.has_real_import())
    has_profile = bool(getattr(session, "profile_id", None))
    cache_ok = _cache_ready(session)
    has_viewed = cache_ok and int(getattr(session, "current_frame", 0) or 0) >= 1
    has_results = bool(getattr(session, "last_results", None))

    specs = [
        ("project", "projects", "Create or open a project", "Создать или открыть проект", True, "project", has_project),
        ("import", "import", "Import MAT data", "Импортировать MAT-данные", True, "import", has_data),
        ("profile", "profile", "Confirm instrument profile", "Подтвердить профиль прибора", True, "profiles", has_project and has_profile),
        ("audit_cache", "audit", "Audit data and build cache", "Аудит данных и создание кэша", True, "cache", cache_ok),
        ("viewer", "viewer", "View ionograms", "Просмотреть ионограммы", True, "viewer", has_viewed),
        ("select", "batch", "Select frames or time interval", "Выбрать кадры или интервал", True, "batch", has_results),
        ("pipeline", "pipeline", "Choose an analysis pipeline", "Выбрать конвейер анализа", False, "pipeline", False),
        ("run", "batch", "Run analysis", "Запустить анализ", True, "batch", has_results),
        ("results", "results", "Inspect results and alternatives", "Проверить результаты и альтернативы", True, "results", has_results),
        ("expert", "expert", "Add expert decisions", "Добавить решения эксперта", False, "expert", False),
        ("export", "reports", "Export a report", "Экспортировать отчёт", True, "export", False),
    ]

    # Determine first incomplete required step
    first_open: str | None = None
    for sid, _nav, _en, _ru, required, _help, done in specs:
        if required and not done and sid not in {"pipeline", "expert"}:
            first_open = sid
            break

    # Prerequisite chain for blocking
    prereq_done = True
    out: list[WorkflowStep] = []
    for sid, nav, en, ru, required, help_id, done in specs:
        if not required:
            status: StepStatus = "optional"
        elif done:
            status = "completed"
        elif not prereq_done:
            status = "blocked"
        elif sid == first_open:
            status = "current"
        else:
            status = "incomplete"
        out.append(
            WorkflowStep(
                step_id=sid,
                nav_key=nav,
                title_en=en,
                title_ru=ru,
                status=status,
                required=required,
                help_id=help_id,
            )
        )
        if required and sid not in {"pipeline", "expert"}:
            prereq_done = prereq_done and done
    return out


def next_recommended_step(session: Any) -> WorkflowStep:
    steps = evaluate_workflow(session)
    for s in steps:
        if s.status == "current":
            return s
    for s in steps:
        if s.status == "incomplete" and s.required:
            return s
    return steps[-1]


def next_action_text(session: Any, lang: str = "en") -> str:
    step = next_recommended_step(session)
    if lang == "ru":
        return f"Рекомендуемый шаг: {step.title_ru}"
    return f"Recommended next step: {step.title_en}"

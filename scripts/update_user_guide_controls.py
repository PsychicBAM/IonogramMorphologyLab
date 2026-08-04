#!/usr/bin/env python3
"""Append complete button/control reference tables to USER_GUIDE_EN/RU."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTROLS = [
    # page, ru, en, purpose, prereq, effect, files, source_effect, disabled, errors, help
    ("Home", "Продолжить рекомендуемый шаг", "Continue recommended step",
     "Open next guided page", "Project/workflow state", "Navigates", "—", "None",
     "When no next step", "Missing project", "home"),
    ("Home", "Новый проект", "New Project", "Create project", "Writable workspace",
     "Creates project", "project dir", "None", "Invalid path", "Permission error", "projects"),
    ("Projects", "Создать проект", "Create project", "Initialize analysis project",
     "Writable parent folder", "Writes project metadata", "project DB/files", "None",
     "Empty name", "IO error", "projects"),
    ("Import", "Выбрать файл", "Select file", "Register MAT file", "Active project",
     "Sets active MAT", "inventory", "Read-only source", "No project", "Forbidden path", "import"),
    ("Import", "Выбрать папку", "Select folder", "Register MAT folder", "Active project",
     "Lists MAT files", "inventory", "Read-only source", "No project", "Empty folder", "import"),
    ("Audit", "Обновить аудит", "Refresh audit", "Recompute audit cards", "Active MAT",
     "Shows readiness/warnings", "audit artifacts", "None", "No MAT", "Parse errors", "audit"),
    ("Viewer", "Первый/Пред/След/Последний", "First/Prev/Next/Last", "Frame navigation",
     "Loaded Viewer", "Changes frame", "—", "None", "Not ready", "Render error", "viewer"),
    ("Viewer", "−N мин / +N мин", "−N min / +N min", "Time jump", "Time mapping available",
     "Jumps by minutes", "—", "None", "Mapping unavailable", "Invalid time", "viewer"),
    ("Viewer", "Пуск / Пауза / Цикл", "Play / Pause / Loop", "Playback", "Loaded Viewer",
     "Animates frames", "—", "None", "Not ready", "—", "viewer"),
    ("Viewer", "Кэш", "Cache", "Build derived cache", "Imported MAT", "Builds Zarr cache",
     "cache files", "None", "No MAT", "Disk full", "viewer"),
    ("Viewer", "Контактный лист", "Contact sheet", "Sequence sheet", "Cache preferred",
     "Writes sheet PNG", "PNG", "None", "No frames", "Render error", "sequences"),
    ("Viewer", "Сохранить PNG", "Save PNG", "Export current view", "Rendered frame",
     "Writes PNG", "PNG", "None", "No image", "IO error", "viewer"),
    ("Batch", "Старт", "Start", "Run selected pipeline", "Valid selection",
     "Creates run + predictions", "run root JSON", "None", "Invalid selection",
     "Stage failures", "batch"),
    ("Batch", "Пауза / Продолжить / Отмена", "Pause / Resume / Cancel", "Control run",
     "Running batch", "Pauses/resumes/cancels", "partial run", "None", "Not running", "—", "batch"),
    ("Results", "Экспорт", "Export", "Open report export", "last_run_root",
     "Writes reports", "HTML/CSV/JSON", "None", "No run", "Export error", "reports"),
    ("Results", "Добавить в набор экспертной проверки", "Add to review dataset",
     "Owner-review label", "Selected result row", "Saves owner-reviewed label",
     "review_dataset/labels/*.json", "None", "No selection / forbidden source",
     "Article 3 blocked", "expert"),
    ("Results", "Принять / Изменить / Неопределённо / N/A", "Accept / Change / Uncertain / N/A",
     "Human decision on result", "Selected result", "Records human decision",
     "human decision files", "None", "No selection", "Reason required", "expert"),
    ("Results", "Столбцы", "Columns", "Configure visible columns", "Results loaded",
     "Rebuilds table columns", "—", "None", "—", "—", "results"),
    ("Reports", "Экспорт", "Export", "Write bilingual reports", "last_run_root",
     "Creates report set", "reports/*", "None", "No run", "IO error", "reports"),
    ("MATLAB Studio", "Запустить", "Run", "Execute selected script", "Backend + script + MAT",
     "Managed job; Studio results", "run output folder", "None if allow_write off",
     "No script/backend", "MATLAB/Octave error", "matlab"),
    ("MATLAB Studio", "Остановить", "Cancel", "Cancel running job", "Running job",
     "Requests cancel", "partial outputs kept", "None", "Idle", "—", "matlab"),
    ("MATLAB Studio", "Форматировать код", "Format code", "Indent editor text", "Editor open",
     "Whitespace-only format", "—", "None", "—", "—", "matlab"),
    ("MATLAB Studio", "Проверить", "Validate", "Basic editor validation", "Editor open",
     "Shows warnings", "—", "None", "—", "Empty script", "matlab"),
    ("MATLAB Studio", "Сохранить копию", "Save copy", "Save .m copy", "Editor text",
     "Writes .m", ".m file", "None", "Cancel dialog", "IO error", "matlab"),
    ("MATLAB Studio", "Сравнить с оригиналом", "Compare with original", "Diff editor vs saved",
     "Script id", "Shows unified diff", "—", "None", "—", "—", "matlab"),
    ("MATLAB Studio", "Открыть папку результатов", "Open Results Folder", "Open run folder",
     "Completed/failed run with work_dir", "Opens folder", "—", "None", "No work_dir", "Missing folder", "matlab"),
    ("MATLAB Studio", "Зарегистрировать как плагин MATLAB", "Register as MATLAB Plugin",
     "Create plugin manifest", "Successful complete run", "Writes manifest",
     "iml-matlab.yaml", "None", "Failed/incomplete run", "Wizard refuses", "matlab"),
    ("MATLAB Studio", "Добавить в сравнение методов", "Add to Method Comparison",
     "Hand-off candidates", "Candidates present", "Prepares comparison payload; not main Results",
     "—", "None", "No candidates", "—", "compare"),
    ("Model Lab", "Импорт размеченного CSV…", "Import labeled CSV…", "Load training CSV",
     "Valid CSV", "Loads dataset", "—", "None", "Cancel", "Validation error (localized)", "models"),
    ("Model Lab", "Собрать синтетический набор", "Build synthetic development set",
     "Create synthetic CSV", "Writable model_lab", "Writes synthetic_dev.csv",
     "model_lab/datasets", "None", "—", "Feature errors", "models"),
    ("Model Lab", "Обучить", "Train", "Train development model", "Dataset loaded",
     "Writes model card", "model_lab models", "None", "No dataset", "Missing values / train error", "models"),
    ("Model Lab", "Включить выбранную модель в анализ", "Enable selected model in analysis",
     "Opt-in ML stage", "Selected model + trust", "Sets enabled_model_ids", "settings",
     "None", "No selection / trust declined", "Foreign model warning", "models"),
    ("Settings", "Сохранить / Сброс", "Save / Reset", "Persist or reload settings", "—",
     "Writes settings store", "settings file", "None", "—", "IO error", "settings"),
    ("Settings", "Язык интерфейса", "Interface language", "Switch EN/RU", "—",
     "Retranslates UI", "settings", "None", "—", "—", "settings"),
    ("Settings", "Масштаб интерфейса", "Interface scale", "UI scale percent", "—",
     "Applies scale preference", "settings", "None", "—", "—", "settings"),
    ("Help", "Восстановить введения", "Restore introductions", "Restore page intros", "—",
     "Shows intro panels", "settings", "None", "—", "—", "help"),
]


def _table(lang: str) -> str:
    lines = []
    if lang == "en":
        lines.append("## Complete control reference (matches UI 1.1.1)\n")
        lines.append(
            "| Page | RU label | EN label | Purpose | Prerequisites | Immediate effect | "
            "Files created | Source-data effect | Disabled when | Possible errors | Help topic |\n"
            "|------|----------|----------|---------|---------------|------------------|"
            "----------------|--------------------|---------------|-----------------|------------|"
        )
    else:
        lines.append("## Полный справочник элементов управления (UI 1.1.1)\n")
        lines.append(
            "| Страница | Подпись RU | Подпись EN | Назначение | Предпосылки | Немедленный эффект | "
            "Создаваемые файлы | Влияние на исходные данные | Когда отключено | Возможные ошибки | Тема справки |\n"
            "|----------|------------|------------|------------|-------------|--------------------|"
            "--------------------|---------------------------|-----------------|------------------|-------------|"
        )
    for row in CONTROLS:
        page, ru, en, purpose, pre, effect, files, source, disabled, errors, help_topic = row
        lines.append(
            f"| {page} | {ru} | {en} | {purpose} | {pre} | {effect} | {files} | {source} | "
            f"{disabled} | {errors} | {help_topic} |"
        )
    lines.append("")
    lines.append(
        "Scientific status on Results is always one of: Automatic candidate / Owner-reviewed / Expert-confirmed. "
        "Default automatic rows must never be read as confirmed classifications."
        if lang == "en"
        else "Научный статус на странице «Результаты»: Автоматический кандидат / Проверено владельцем / Подтверждено экспертом. "
        "Автоматические строки нельзя считать подтверждённой классификацией."
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    for name, lang in (("USER_GUIDE_EN.md", "en"), ("USER_GUIDE_RU.md", "ru")):
        path = ROOT / "docs" / name
        text = path.read_text(encoding="utf-8")
        marker = "## Complete control reference" if lang == "en" else "## Полный справочник элементов управления"
        if marker in text:
            text = text.split(marker)[0].rstrip() + "\n\n"
        path.write_text(text.rstrip() + "\n\n" + _table(lang), encoding="utf-8")
        print("updated", path)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Regenerate documentation SVG screenshot placeholders (idempotent, no private data)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "assets" / "screenshots"

W, H = 960, 540
BG = "#eef1f5"
TITLE_BG = "#1e3a5f"
TITLE_FG = "#ffffff"
PANEL_BG = "#ffffff"
PANEL_BORDER = "#b8c4d4"
LABEL = "#5a6a7a"
ACCENT = "#2a6fdb"


def _svg(title: str, panels: list[tuple[str, str]], *, lang: str = "ru") -> str:
    """Build a simple UI mock: title bar + labeled panels."""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<rect width="{W}" height="44" fill="{TITLE_BG}"/>',
        f'<circle cx="22" cy="22" r="7" fill="#e74c3c"/>',
        f'<circle cx="42" cy="22" r="7" fill="#f1c40f"/>',
        f'<circle cx="62" cy="22" r="7" fill="#2ecc71"/>',
        f'<text x="90" y="28" fill="{TITLE_FG}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="16" font-weight="600">{title}</text>',
        f'<text x="{W - 16}" y="28" fill="{TITLE_FG}" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="11" text-anchor="end">IML 1.1.1 · {lang.upper()}</text>',
    ]
    n = len(panels)
    if n == 1:
        layouts = [(16, 56, W - 32, H - 72)]
    elif n == 2:
        layouts = [(16, 56, W - 32, (H - 72) // 2 - 8), (16, 56 + (H - 72) // 2 + 8, W - 32, (H - 72) // 2 - 8)]
    elif n == 3:
        pw = (W - 48) // 2
        ph = (H - 80) // 2
        layouts = [
            (16, 56, pw, ph),
            (32 + pw, 56, pw, ph),
            (16, 64 + ph, W - 32, H - 80 - ph),
        ]
    else:
        cols = 2
        rows = (n + cols - 1) // cols
        pw = (W - 48) // cols
        ph = (H - 80) // rows
        layouts = []
        for i in range(n):
            c, r = i % cols, i // cols
            layouts.append((16 + c * (pw + 16), 56 + r * (ph + 8), pw, ph - 8))

    for (label, hint), (x, y, pw, ph) in zip(panels, layouts):
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="{pw}" height="{ph}" rx="6" fill="{PANEL_BG}" '
                f'stroke="{PANEL_BORDER}" stroke-width="1.5"/>',
                f'<text x="{x + 12}" y="{y + 22}" fill="{LABEL}" font-family="Segoe UI, Arial, sans-serif" '
                f'font-size="11" font-weight="600">{label}</text>',
                f'<line x1="{x + 12}" y1="{y + 30}" x2="{x + pw - 12}" y2="{y + 30}" '
                f'stroke="{PANEL_BORDER}" stroke-width="1"/>',
                f'<rect x="{x + 12}" y="{y + 40}" width="{pw - 24}" height="{max(ph - 52, 20)}" '
                f'rx="4" fill="{BG}"/>',
            ]
        )
        if hint:
            parts.append(
                f'<text x="{x + 20}" y="{y + 58}" fill="{ACCENT}" font-family="Segoe UI, Arial, sans-serif" '
                f'font-size="10">{hint}</text>'
            )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


SCREENS: dict[str, dict] = {
    "home_workflow_ru.svg": {
        "title": "Главная — рекомендуемый порядок работы",
        "lang": "ru",
        "panels": [
            ("Статус проекта", "Проект: учебный синтетический"),
            ("Шаги workflow", "● Текущий · ○ Заблокирован · ✓ Выполнен"),
            ("Быстрые действия", "Продолжить · Создать проект"),
        ],
    },
    "home_workflow_en.svg": {
        "title": "Home — recommended workflow",
        "lang": "en",
        "panels": [
            ("Project status", "Project: synthetic teaching"),
            ("Workflow steps", "● Current · ○ Blocked · ✓ Done"),
            ("Quick actions", "Continue · Create project"),
        ],
    },
    "mat_import_ru.svg": {
        "title": "Импорт MAT — аудит данных",
        "lang": "ru",
        "panels": [
            ("Выбор файла", "synthetic_demo.mat"),
            ("Инвентаризация переменных", "Amp_all · форма · SHA"),
            ("Журнал аудита", "valid · без изменения источника"),
        ],
    },
    "instrument_profile_ru.svg": {
        "title": "Профиль прибора",
        "lang": "ru",
        "panels": [
            ("Выбранный профиль", "kfu_cyclone (провизорный)"),
            ("Соответствие переменных", "Amp_all → кадры × частоты"),
            ("Предупреждения", "Gate2: метрология открыта"),
        ],
    },
    "ionogram_viewer_ru.svg": {
        "title": "Просмотр ионограмм",
        "lang": "ru",
        "panels": [
            ("Кадр и время", "Кадр 42 · мин. 41"),
            ("Изображение", "[ синтетическая ионограмма ]"),
            ("Навигация", "◀ ▶ · шаг 10 мин"),
        ],
    },
    "contact_sheet_ru.svg": {
        "title": "Контактный лист",
        "lang": "ru",
        "panels": [
            ("Сетка", "5×5 · шаг 10 мин"),
            ("Предпросмотр", "[ миниатюры кадров ]"),
            ("Сводка", "25 кадров · интервал 4 ч"),
        ],
    },
    "results_ru.svg": {
        "title": "Результаты анализа",
        "lang": "ru",
        "panels": [
            ("Таблица кадров", "морфология · слой · качество"),
            ("Альтернативы", "кандидаты и воздержание"),
            ("Экспорт", "CSV · JSON · HTML"),
        ],
    },
    "rule_builder_ru.svg": {
        "title": "Rule Builder — правило без кода",
        "lang": "ru",
        "panels": [
            ("Мастер", "цель → условия → источник"),
            ("Предпросмотр RU/EN", "кандидатное правило"),
            ("Примеры", "скопировать в черновик"),
        ],
    },
    "rule_testing_ru.svg": {
        "title": "Rule Testing Lab",
        "lang": "ru",
        "panels": [
            ("Выбор правила", "черновик / пакет"),
            ("Перебор порогов", "sweep · метрики"),
            ("Отчёт теста", "синтетика · development"),
        ],
    },
    "matlab_studio_ru.svg": {
        "title": "MATLAB Studio",
        "lang": "ru",
        "panels": [
            ("Библиотека скриптов", "manifest · версия"),
            ("Редактор", "function detect_layer …"),
            ("Журнал запуска", "diary · артефакты"),
        ],
    },
    "method_comparison_ru.svg": {
        "title": "Сравнение методов",
        "lang": "ru",
        "panels": [
            ("Методы", "встроенный · MATLAB · правила"),
            ("Разногласия", "оси · ограничения"),
            ("Сводка", "согласие не = валидация"),
        ],
    },
    "pipeline_builder_ru.svg": {
        "title": "Конструктор конвейера",
        "lang": "ru",
        "panels": [
            ("Операции", "аудит · кэш · признаки · правила"),
            ("Порядок", "drag · enable/disable"),
            ("Запуск", "пауза · отмена · журнал"),
        ],
    },
    "settings_ru.svg": {
        "title": "Настройки",
        "lang": "ru",
        "panels": [
            ("Общие", "язык · UX guided/research/expert"),
            ("Анализ", "scientific_strict (отдельно от UX)"),
            ("Производительность", "кэш · workers · RAM"),
        ],
    },
    "help_ru.svg": {
        "title": "Справка",
        "lang": "ru",
        "panels": [
            ("Поиск", "своё правило · медленно · O/X"),
            ("Разделы", "86 тем · RU/EN"),
            ("Связанные темы", "workflow · Rule Builder"),
        ],
    },
}


def generate_all() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, spec in SCREENS.items():
        path = OUT_DIR / name
        content = _svg(spec["title"], spec["panels"], lang=spec.get("lang", "ru"))
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    paths = generate_all()
    print(f"Wrote {len(paths)} SVG placeholders to {OUT_DIR.relative_to(ROOT)}/")
    for p in paths:
        print(f"  - {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

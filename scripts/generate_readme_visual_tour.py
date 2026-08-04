#!/usr/bin/env python3
"""Rewrite README.md / README_RU.md with collapsible screenshot visual tour."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT = "docs/assets/screenshots/v1.1.1"

PAGES = [
    ("Home", "Главная", "home", "home",
     "Entry dashboard and recommended workflow.",
     "Стартовая панель и рекомендуемый рабочий процесс.",
     "At first launch or when choosing the next safe step.",
     "При первом запуске или выборе следующего безопасного шага.",
     "Writable project workspace.",
     "Доступная для записи рабочая область проекта.",
     "Continue recommended step; UX mode; New Project.",
     "Продолжить рекомендуемый шаг; режим UX; Новый проект.",
     "Opens the next guided page or creates a project.",
     "Открывает следующую страницу или создаёт проект.",
     "Project folder / navigation change.",
     "Папка проекта / смена навигации.",
     "Skipping Import before Viewer.",
     "Пропуск импорта перед Просмотрщиком.",
     "Does not analyse frames by itself.",
     "Сама по себе не анализирует кадры.",
     "Projects or Import.",
     "Проекты или Импорт."),
    ("Projects", "Проекты", "projects", "project_creation",
     "Create and select an analysis project.",
     "Создание и выбор проекта анализа.",
     "Before importing MAT data.",
     "До импорта MAT-данных.",
     "Writable workspace path.",
     "Путь к записываемой рабочей области.",
     "Project name; Create project.",
     "Имя проекта; Создать проект.",
     "Creates project metadata under the workspace.",
     "Создаёт метаданные проекта в рабочей области.",
     "Project directory and database rows.",
     "Каталог проекта и записи БД.",
     "Creating inside the portable EXE folder.",
     "Создание внутри папки portable EXE.",
     "Project creation does not validate science.",
     "Создание проекта не валидирует науку.",
     "Import.",
     "Импорт."),
    ("Import", "Импорт", "import", "mat_import",
     "Select MAT file/folder without rewriting source.",
     "Выбор MAT-файла/папки без перезаписи источника.",
     "After a project exists.",
     "После создания проекта.",
     "Active project.",
     "Активный проект.",
     "Select file; Select folder; Technical details.",
     "Выбрать файл; Выбрать папку; Технические сведения.",
     "Registers source path and inventory.",
     "Регистрирует путь источника и инвентарь.",
     "Inventory / audit artifacts only.",
     "Только инвентарь / артефакты аудита.",
     "Expecting IML to rewrite Amp_all.",
     "Ожидание, что IML перезапишет Amp_all.",
     "Import does not classify morphology.",
     "Импорт не классифицирует морфологию.",
     "Data Audit / Profile.",
     "Проверка данных / Профиль."),
    ("Profile", "Профиль", "profile", "instrument_profile",
     "Instrument axes, time mapping, verification status.",
     "Оси прибора, привязка времени, статус проверки.",
     "Before Viewer or Batch.",
     "До Просмотрщика или Пакета.",
     "Imported MAT + chosen profile id.",
     "Импортированный MAT + id профиля.",
     "Profile selectors; provisional warnings.",
     "Выбор профиля; предупреждения о provisional.",
     "Loads axes labels and time mapping.",
     "Загружает подписи осей и привязку времени.",
     "None to source MAT.",
     "Не изменяет исходный MAT.",
     "Treating provisional axes as metrology.",
     "Принятие provisional осей за метрологию.",
     "Nominal virtual height is not true height.",
     "Номинальная виртуальная высота ≠ истинная.",
     "Audit or Viewer.",
     "Аудит или Просмотрщик."),
    ("Audit", "Аудит", "audit", "data_audit",
     "Quality and inventory checks for the active MAT.",
     "Проверки качества и инвентаря активного MAT.",
     "After Import, before trusting Batch.",
     "После Импорта, до доверия Пакету.",
     "Active MAT.",
     "Активный MAT.",
     "Run audit / refresh cards.",
     "Запуск аудита / обновление карточек.",
     "Shows variable shapes, warnings, readiness.",
     "Показывает формы переменных, предупреждения, готовность.",
     "Audit report under project/workspace.",
     "Отчёт аудита в проекте/workspace.",
     "Ignoring blocking quality warnings.",
     "Игнорирование блокирующих предупреждений.",
     "Audit ≠ morphology classification.",
     "Аудит ≠ классификация морфологии.",
     "Viewer.",
     "Просмотрщик."),
    ("Viewer", "Просмотрщик", "viewer", "ionogram_viewer",
     "Inspect frames; collapsible summary; Navigation/Jump/Playback/Display.",
     "Просмотр кадров; сворачиваемая сводка; Навигация/Скачок/Воспроизведение/Отображение.",
     "When inspecting evidence before/after analysis.",
     "При просмотре доказательств до/после анализа.",
     "Imported MAT + profile + optional cache.",
     "Импортированный MAT + профиль + опциональный кэш.",
     "First/Prev/Next/Last; ±N min; Play/Pause/Loop; Cache/Contact/Save; View/Preview.",
     "Первый/Пред/След/Послед; ±N мин; Пуск/Пауза/Цикл; Кэш/Контакт/Сохранить; Вид/Предпросмотр.",
     "Renders current frame; builds derived cache on demand.",
     "Отрисовывает текущий кадр; кэш по запросу.",
     "Derived cache / PNG exports only.",
     "Только производный кэш / PNG.",
     "Relying on fast preview as scientific proof.",
     "Опора на быстрый предпросмотр как научное доказательство.",
     "Display modes are diagnostic, not URSI scaling.",
     "Режимы отображения — диагностика, не URSI-скейлинг.",
     "Temporal Sequences or Batch.",
     "Временные последовательности или Пакет."),
    ("Temporal Sequences", "Временные последовательности", "sequences", "contact_sheet",
     "Build contact sheets / sequence views.",
     "Контактные листы / последовательности.",
     "When reviewing time evolution.",
     "При просмотре эволюции во времени.",
     "Ready Viewer cache preferred.",
     "Желателен готовый кэш Просмотрщика.",
     "Build contact sheet.",
     "Создать контактный лист.",
     "Writes a contact-sheet image.",
     "Пишет изображение контактного листа.",
     "PNG under workspace/reports.",
     "PNG в workspace/reports.",
     "Using contact sheet as sole morphology proof.",
     "Контактный лист как единственное доказательство.",
     "Temporal context is optional for default analysis.",
     "Временной контекст необязателен для анализа по умолчанию.",
     "Batch Analysis.",
     "Пакетный анализ."),
    ("Batch Analysis", "Пакетный анализ", "batch", "batch_analysis",
     "Select frames and run the default Python pipeline.",
     "Выбор кадров и запуск конвейера Python по умолчанию.",
     "When producing automatic candidates.",
     "Когда нужны автоматические кандидаты.",
     "Project + MAT + profile.",
     "Проект + MAT + профиль.",
     "Mode/preset/stages; Start/Pause/Resume/Cancel; Technical log.",
     "Режим/пресет/этапы; Старт/Пауза/Продолжить/Отмена; Техжурнал.",
     "Runs audit→features→RuleEngine→reports as selected.",
     "Запускает аудит→признаки→RuleEngine→отчёты.",
     "Run root with predictions JSON.",
     "Корень запуска с predictions JSON.",
     "Assuming MATLAB/Model Lab ran automatically.",
     "Предположение, что MATLAB/Model Lab шли автоматически.",
     "Default path does not use MATLAB scripts or ML models.",
     "Путь по умолчанию не использует MATLAB/ML.",
     "Results.",
     "Результаты."),
    ("Results", "Результаты", "results", "results",
     "Compact table + details; pipeline panel; review dataset; diffuse why.",
     "Компактная таблица + детали; панель конвейера; набор проверки; почему тип не определён.",
     "After Batch completes.",
     "После завершения Пакета.",
     "last_run_root with predictions.",
     "last_run_root с predictions.",
     "Filter; columns; Export; Add to review dataset; Accept/Change/…",
     "Фильтр; столбцы; Экспорт; Добавить в набор проверки; Принять/Изменить/…",
     "Shows Automatic candidate status and evidence.",
     "Показывает статус «Автоматический кандидат» и доказательства.",
     "Exports / owner-review labels.",
     "Экспорт / метки владельца.",
     "Reading automatic as expert-confirmed.",
     "Чтение автоматики как подтверждения эксперта.",
     "Candidates are not confirmed classifications.",
     "Кандидаты — не подтверждённые классификации.",
     "Expert Review or Reports.",
     "Экспертная проверка или Отчёты."),
    ("Parameters", "Параметры", "parameters", "parameters",
     "Documented parameter proposals / limits.",
     "Документированные предложения параметров / пределы.",
     "When reviewing parameter-related claims.",
     "При проверке параметрических утверждений.",
     "Active project context.",
     "Контекст активного проекта.",
     "Parameter forms / save actions on page.",
     "Формы параметров / сохранение на странице.",
     "Records provisional parameter proposals.",
     "Записывает provisional предложения параметров.",
     "Config under project.",
     "Конфиг в проекте.",
     "Treating proposals as calibrated foF2.",
     "Принятие предложений за калиброванный foF2.",
     "Not a substitute for expert scaling.",
     "Не заменяет экспертный скейлинг.",
     "Results / Reports.",
     "Результаты / Отчёты."),
    ("Expert Review", "Экспертная проверка", "expert", "expert_review",
     "Guided entry to owner/expert decisions via Results.",
     "Вход к решениям владельца/эксперта через Результаты.",
     "When human labels are needed.",
     "Когда нужны человеческие метки.",
     "Existing results row.",
     "Существующая строка результата.",
     "Open Results; Add to review dataset (on Results).",
     "Открыть Результаты; Добавить в набор (на Результатах).",
     "Navigates to Results review workflow.",
     "Ведёт к рабочему процессу Результаты.",
     "Review-dataset JSON labels.",
     "JSON-метки набора проверки.",
     "Calling owner-reviewed expert-confirmed.",
     "Называть проверку владельца экспертной.",
     "Owner-reviewed ≠ expert-confirmed.",
     "Проверено владельцем ≠ подтверждено экспертом.",
     "Results.",
     "Результаты."),
    ("Reports", "Отчёты", "reports", "reports",
     "Export bilingual reproducible reports.",
     "Экспорт двуязычных воспроизводимых отчётов.",
     "After a run exists.",
     "После появления запуска.",
     "last_run_root.",
     "last_run_root.",
     "Export.",
     "Экспорт.",
     "Writes HTML/CSV/JSON/MD with provenance.",
     "Пишет HTML/CSV/JSON/MD с происхождением.",
     "Report files under run/reports.",
     "Файлы отчётов в run/reports.",
     "Sharing without provenance review.",
     "Публикация без проверки provenance.",
     "Reports do not upgrade candidate status.",
     "Отчёты не повышают статус кандидата.",
     "Settings / archive.",
     "Настройки / архив."),
    ("Reference Atlas", "Эталонный атлас", "atlas", "reference_atlas",
     "Metadata-linked reference wording (images may be unavailable).",
     "Эталонные формулировки по метаданным (изображения могут быть недоступны).",
     "When comparing wording / citations.",
     "При сравнении формулировок / цитат.",
     "Atlas pack installed.",
     "Установлен пакет атласа.",
     "Filter; entry list; detail fields.",
     "Фильтр; список; поля деталей.",
     "Shows localized field labels; source titles preserved.",
     "Локализованные подписи полей; названия источников сохраняются.",
     "None to source MAT.",
     "Не меняет исходный MAT.",
     "Assuming pixel-to-pixel atlas matching.",
     "Предположение о попиксельном сравнении с атласом.",
     "Default analysis uses metadata hints only.",
     "Анализ по умолчанию использует только метаданные.",
     "Scientific Basis.",
     "Научная основа."),
    ("Scientific Basis", "Научная основа", "science", "scientific_basis",
     "Claims, sources, limitations in EN/RU labels.",
     "Утверждения, источники, ограничения с подписями EN/RU.",
     "When documenting scientific grounding.",
     "При документировании научной базы.",
     "Bundled science content.",
     "Встроенный научный контент.",
     "Section browser / technical pane.",
     "Обзор разделов / техническая панель.",
     "Displays translated labels; originals preserved.",
     "Показывает переведённые подписи; оригиналы сохраняются.",
     "None.",
     "Нет.",
     "Confusing claim text with automatic validation.",
     "Путать текст утверждений с автоматической валидацией.",
     "Does not change RuleEngine thresholds.",
     "Не меняет пороги RuleEngine.",
     "Rule Builder / Help.",
     "Конструктор правил / Справка."),
    ("MATLAB Studio", "MATLAB Studio", "matlab", "matlab_studio",
     "Library, editor, managed run, result tabs.",
     "Библиотека, редактор, управляемый запуск, вкладки результата.",
     "When testing optional MATLAB methods.",
     "При проверке опциональных методов MATLAB.",
     "Configured backend + selected script + MAT.",
     "Настроенный backend + скрипт + MAT.",
     "Format/Validate/Run/Cancel/Save copy/Compare; result actions.",
     "Формат/Проверить/Запуск/Отмена/Копия/Сравнить; действия результата.",
     "Runs script via JobManager; shows Studio results only.",
     "Запускает скрипт через JobManager; показывает только Studio-результаты.",
     "Run-specific output folder.",
     "Папка конкретного запуска.",
     "Assuming Studio output entered main Results.",
     "Предположение, что вывод Studio попал в Результаты.",
     "Not part of default automatic analysis.",
     "Не входит в автоматический анализ по умолчанию.",
     "Method Comparison / Pipeline Builder.",
     "Сравнение методов / Конструктор конвейера."),
    ("Rule Builder", "Конструктор правил", "rules", "rule_builder",
     "Author versioned rule packs with citations.",
     "Создание версионированных пакетов правил с цитатами.",
     "When extending development rules carefully.",
     "При осторожном расширении правил разработки.",
     "Writable rules workspace.",
     "Записываемая область правил.",
     "Wizard fields; save/export pack.",
     "Поля мастера; сохранить/экспорт пакета.",
     "Writes rule pack metadata.",
     "Пишет метаданные пакета правил.",
     "Rule pack files.",
     "Файлы пакета правил.",
     "Enabling unsupported URSI numeric thresholds.",
     "Включение неподдерживаемых числовых порогов URSI.",
     "Custom rules need independent validation.",
     "Пользовательские правила требуют независимой валидации.",
     "Rule Testing.",
     "Тестирование правил."),
    ("Rule Testing", "Тестирование правил", "rule_test", "rule_testing",
     "Test rule packs against labeled or synthetic cases.",
     "Проверка пакетов правил на размеченных/синтетических случаях.",
     "After editing a rule pack.",
     "После правки пакета правил.",
     "Rule pack + test cases.",
     "Пакет правил + тест-кейсы.",
     "Run tests / view diffs.",
     "Запуск тестов / просмотр различий.",
     "Shows pass/fail and disagreements.",
     "Показывает pass/fail и разногласия.",
     "Test reports under workspace.",
     "Отчёты тестов в workspace.",
     "Treating synthetic pass as external validation.",
     "Считать синтетический pass внешней валидацией.",
     "Not a substitute for expert-confirmed datasets.",
     "Не заменяет экспертно подтверждённые наборы.",
     "Results / Method Comparison.",
     "Результаты / Сравнение методов."),
    ("Method Comparison", "Сравнение методов", "compare", "method_comparison",
     "Side-by-side Python / MATLAB / ML / expert rows.",
     "Сопоставление строк Python / MATLAB / ML / эксперт.",
     "When multiple candidates exist.",
     "Когда есть несколько кандидатов.",
     "Analysis result and/or MATLAB candidates.",
     "Результат анализа и/или кандидаты MATLAB.",
     "Refresh.",
     "Обновить.",
     "Displays separate axes; no automatic winner.",
     "Показывает раздельные оси; без автоматического победителя.",
     "None unless exported.",
     "Нет, пока не экспортировано.",
     "Assuming one method is declared correct.",
     "Предположение, что один метод объявлен верным.",
     "Comparison does not fuse ensembles by default.",
     "Сравнение не делает ensemble по умолчанию.",
     "Pipeline Builder.",
     "Конструктор конвейера."),
    ("Pipeline Builder", "Конструктор конвейера", "pipeline", "pipeline_builder",
     "Compose optional stages (does not silently enable MATLAB/ML).",
     "Сборка опциональных этапов (не включает MATLAB/ML молча).",
     "When documenting a custom stage order.",
     "При документировании порядка этапов.",
     "Project context.",
     "Контекст проекта.",
     "Stage toggles / save pipeline.",
     "Переключатели этапов / сохранить конвейер.",
     "Stores pipeline definition for later runs.",
     "Сохраняет определение конвейера для запусков.",
     "Pipeline config files.",
     "Файлы конфигурации конвейера.",
     "Enabling untrusted plugins without review.",
     "Включение недоверенных плагинов без проверки.",
     "Default Batch path remains Python RuleEngine unless changed.",
     "Пакет по умолчанию остаётся Python RuleEngine, пока не изменён.",
     "Batch Analysis.",
     "Пакетный анализ."),
    ("Model Lab", "Лаборатория моделей", "models", "model_lab",
     "Development ML train/compare; disabled in default analysis.",
     "Обучение/сравнение ML для разработки; в анализе по умолчанию выключено.",
     "Research prototyping only.",
     "Только исследовательское прототипирование.",
     "Labeled CSV or synthetic set.",
     "Размеченный CSV или синтетический набор.",
     "Import CSV; Build synthetic; Train; Enable model.",
     "Импорт CSV; Синтетика; Обучить; Включить модель.",
     "Trains development models with local metrics.",
     "Обучает модели разработки с локальными метриками.",
     "Model cards under model_lab/.",
     "Карточки моделей в model_lab/.",
     "Enabling foreign joblib without trust prompt care.",
     "Включение чужого joblib без осторожности к trust.",
     "Not externally validated; not default pipeline.",
     "Не валидировано внешне; не конвейер по умолчанию.",
     "Settings / Method Comparison.",
     "Настройки / Сравнение методов."),
    ("Settings", "Настройки", "settings", "settings",
     "Language, scale, storage, MATLAB backends, privacy.",
     "Язык, масштаб, хранение, backend MATLAB, приватность.",
     "Anytime configuration is needed.",
     "Когда нужна конфигурация.",
     "Writable settings store.",
     "Записываемое хранилище настроек.",
     "Tabs General…Advanced; Save/Reset; Storage actions.",
     "Вкладки Общие…Дополнительно; Сохранить/Сброс; действия Storage.",
     "Persists preferences; never rewrites source MAT.",
     "Сохраняет предпочтения; не переписывает исходный MAT.",
     "settings store / shortcuts.",
     "хранилище настроек / ярлыки.",
     "Pointing cache into source data folders.",
     "Кэш внутри папок исходных данных.",
     "Settings do not change scientific thresholds silently.",
     "Настройки не меняют научные пороги молча.",
     "Help.",
     "Справка."),
    ("Help", "Справка", "help", "help",
     "In-app topics and restore intros.",
     "Темы справки и восстановление введений.",
     "When a control meaning is unclear.",
     "Когда неясен смысл элемента.",
     "Bundled help content.",
     "Встроенное содержимое справки.",
     "Search; topic list; Restore introductions.",
     "Поиск; список тем; Восстановить введения.",
     "Shows localized help body.",
     "Показывает локализованный текст справки.",
     "None.",
     "Нет.",
     "Skipping Help when results look 'confirmed'.",
     "Пропуск Справки, когда результат выглядит «подтверждённым».",
     "Help text is guidance, not validation.",
     "Текст справки — руководство, не валидация.",
     "Return to Home workflow.",
     "Вернуться к процессу на Главной."),
]


def _details(lang: str, page: tuple) -> str:
    (en, ru, _key, stem, purpose_en, purpose_ru, when_en, when_ru, pre_en, pre_ru,
     ctrl_en, ctrl_ru, effect_en, effect_ru, out_en, out_ru, mistake_en, mistake_ru,
     lim_en, lim_ru, next_en, next_ru) = page
    title = ru if lang == "ru" else en
    purpose = purpose_ru if lang == "ru" else purpose_en
    when = when_ru if lang == "ru" else when_en
    pre = pre_ru if lang == "ru" else pre_en
    ctrl = ctrl_ru if lang == "ru" else ctrl_en
    effect = effect_ru if lang == "ru" else effect_en
    out = out_ru if lang == "ru" else out_en
    mistake = mistake_ru if lang == "ru" else mistake_en
    lim = lim_ru if lang == "ru" else lim_en
    nxt = next_ru if lang == "ru" else next_en
    labels = {
        "purpose": ("Назначение", "Purpose"),
        "when": ("Когда использовать", "When to use"),
        "pre": ("Предпосылки", "Prerequisites"),
        "ctrl": ("Элементы управления", "Controls"),
        "effect": ("Эффект", "Effect"),
        "out": ("Выход", "Output"),
        "mistake": ("Частая ошибка", "Common mistake"),
        "lim": ("Научное ограничение", "Scientific limitation"),
        "next": ("Следующий шаг", "Next step"),
    }
    i = 0 if lang == "ru" else 1
    img = f"{SHOT}/{stem}_{lang}.png"
    return f"""
<details>
<summary><strong>{title}</strong></summary>

![{title}]({img})

- **{labels['purpose'][i]}:** {purpose}
- **{labels['when'][i]}:** {when}
- **{labels['pre'][i]}:** {pre}
- **{labels['ctrl'][i]}:** {ctrl}
- **{labels['effect'][i]}:** {effect}
- **{labels['out'][i]}:** {out}
- **{labels['mistake'][i]}:** {mistake}
- **{labels['lim'][i]}:** {lim}
- **{labels['next'][i]}:** {nxt}

</details>
"""


HEADER_EN = """# Ionogram Morphology Lab

[English](README.md) | [Русский](README_RU.md) · **Release 1.1.1**

Ionogram Morphology Lab (IML) is a bilingual (EN/RU) desktop research application for **source-traceable ionogram morphology analysis**, expert review, rule testing, and report export. It imports user-selected MATLAB (`.mat`) data, preserves provenance, and keeps morphology, ambiguity, quality, and parameter proposals on **separate scientific axes**.

> **Scientific status:** Output is a **candidate** morphology or parameter proposal compatible with image evidence. It does **not** establish a physical mechanism, replace expert scaling, or validate a model. Development models and custom rules require independent, domain-appropriate validation before operational use.

![Home dashboard (English)](docs/assets/screenshots/v1.1.1/home_en.png)

Teaching PNG captures use synthetic projects only under `docs/assets/screenshots/v1.1.1/`.

## Purpose

IML supports ionospheric radio-physics workflows where analysts must inspect frames with documented instrument context, record candidate morphology with uncertainty, apply versioned rules, and export bilingual reports without silently rewriting source data. Core analysis is **local-first** and does not require MATLAB.

## Default automatic analysis (v1.1.1)

Active: data audit · trace/interference segmentation · Python features · Python RuleEngine · reference **metadata** hints · disagreement flags.

Disabled / unavailable by default: MATLAB Studio methods · Model Lab models · ensemble fusion · pixel-to-pixel atlas image matching.

The Results page shows **What this analysis uses** so these boundaries stay visible.

## Installation & quick start

See [User Guide (EN)](docs/USER_GUIDE_EN.md), [Installation](docs/INSTALLATION_EN.md). Portable: unpack, keep files together, use a writable workspace outside the install folder.

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ".[dev]"
python -m ionogram_morphology_lab.app.main
```

1. Choose language · 2. New Project · 3. Start with `synthetic_data/` · 4. Follow Home recommended steps.

## Visual tour (every page)

Screenshots are from the packaged UI with safe synthetic demonstration data. Personal paths and private MAT locations are excluded.
"""

HEADER_RU = """# Ionogram Morphology Lab

[English](README.md) | [Русский](README_RU.md) · **Релиз 1.1.1**

Ionogram Morphology Lab (IML) — двуязычное (EN/RU) настольное исследовательское приложение для **трассируемого анализа морфологии ионограмм**, экспертной проверки, тестирования правил и экспорта отчётов. Импортирует выбранные пользователем MATLAB (`.mat`) данные, сохраняет происхождение и держит морфологию, неоднозначность, качество и параметры на **раздельных научных осях**.

> **Научный статус:** результат — **кандидат** морфологии или предложения параметра. Это **не** доказательство физического механизма, не замена экспертного скейлинга и не валидация модели.

![Главная (RU)](docs/assets/screenshots/v1.1.1/home_ru.png)

Снимки сделаны на синтетических демонстрационных данных: `docs/assets/screenshots/v1.1.1/`.

## Назначение

IML поддерживает радиофизические рабочие процессы: просмотр кадров с документированным контекстом прибора, запись кандидатов с неопределённостью, применение версионированных правил и экспорт отчётов без перезаписи исходных MAT.

## Автоматический анализ по умолчанию (v1.1.1)

Активно: проверка данных · сегментация трассы/помех · признаки Python · RuleEngine · **метаданные** эталонного атласа · флаги разногласий.

Отключено / недоступно по умолчанию: методы MATLAB Studio · модели Model Lab · ансамблевое объединение · попиксельное сравнение с рисунками из книг.

На странице «Результаты» показана панель **«Что используется в этом анализе»**.

## Установка и быстрый старт

См. [Руководство пользователя](docs/USER_GUIDE_RU.md), [Установка](docs/INSTALLATION_RU.md).

1. Выберите язык · 2. Новый проект · 3. Начните с `synthetic_data/` · 4. Следуйте шагам на Главной.

## Визуальный тур (все страницы)

Снимки из упакованного UI на безопасных синтетических данных. Личные пути исключены.
"""

FOOTER_EN = """
## Documentation map

| Document | Role |
|----------|------|
| [USER_GUIDE_EN.md](docs/USER_GUIDE_EN.md) | Complete control reference |
| [USER_GUIDE_RU.md](docs/USER_GUIDE_RU.md) | Полный справочник элементов |
| [SCIENTIFIC_DECISION_MAP.md](docs/SCIENTIFIC_DECISION_MAP.md) | Default analysis path |
| [CLASSIFICATION_VALIDATION_REPORT.md](docs/CLASSIFICATION_VALIDATION_REPORT.md) | Validation status |

## License / citation

See repository `LICENSE` and science claim packs. Cite IML version **1.1.1** with the analysis run id from Reports.
"""

FOOTER_RU = """
## Карта документации

| Документ | Роль |
|----------|------|
| [USER_GUIDE_RU.md](docs/USER_GUIDE_RU.md) | Полный справочник элементов управления |
| [USER_GUIDE_EN.md](docs/USER_GUIDE_EN.md) | Complete control reference |
| [SCIENTIFIC_DECISION_MAP.md](docs/SCIENTIFIC_DECISION_MAP.md) | Путь анализа по умолчанию |

## Лицензия / цитирование

См. `LICENSE` и пакеты научных утверждений. Указывайте версию IML **1.1.1** и id запуска из Отчётов.
"""


def main() -> None:
    en = HEADER_EN + "\n".join(_details("en", p) for p in PAGES) + FOOTER_EN
    ru = HEADER_RU + "\n".join(_details("ru", p) for p in PAGES) + FOOTER_RU
    (ROOT / "README.md").write_text(en, encoding="utf-8")
    (ROOT / "README_RU.md").write_text(ru, encoding="utf-8")
    print("wrote README.md and README_RU.md", len(PAGES), "pages")


if __name__ == "__main__":
    main()

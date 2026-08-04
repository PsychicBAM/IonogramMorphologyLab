#!/usr/bin/env python3
"""Rewrite Complete control reference tables in USER_GUIDE_EN.md / USER_GUIDE_RU.md for Phase 3C."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Columns: page, ru, en, purpose_en, prereq_en, effect_en, files_en, source_en, disabled_en, errors_en, help
# Plus RU translations for purpose/prereq/effect/files/source/disabled/errors
CONTROLS: list[dict[str, str]] = [
    # Home
    dict(page="Home", ru="Продолжить рекомендуемый шаг", en="Continue recommended step",
         pe="Open next guided page", pr="Project/workflow state", ef="Navigates", fi="—", so="None", di="When no next step", er="Missing project", help="home",
         pru="Открыть следующую страницу по подсказке", prr="Состояние проекта/сценария", efr="Переходит на страницу", fir="—", sor="Нет", dir="Нет следующего шага", err="Нет проекта"),
    dict(page="Home", ru="Новый проект", en="New Project",
         pe="Create project", pr="Writable workspace", ef="Creates project", fi="project dir", so="None", di="Invalid path", er="Permission error", help="projects",
         pru="Создать проект", prr="Доступная для записи рабочая область", efr="Создаёт проект", fir="каталог проекта", sor="Нет", dir="Неверный путь", err="Ошибка доступа"),
    # Projects
    dict(page="Projects", ru="Открыть проект", en="Open Project",
         pe="Open existing project file/folder", pr="Valid project on disk", ef="Loads project; clears stale UI", fi="—", so="None", di="Active unresolved job without confirm", er="Invalid project / IO error", help="projects",
         pru="Открыть существующий проект", prr="Корректный проект на диске", efr="Загружает проект; очищает устаревшее состояние", fir="—", sor="Нет", dir="Активная задача без подтверждения", err="Неверный проект / ошибка ввода-вывода"),
    dict(page="Projects", ru="Выбрать папку проекта", en="Choose Project Folder",
         pe="Browse to a project directory", pr="Writable/readable folder", ef="Opens selected project root", fi="—", so="None", di="—", er="Folder not a project", help="projects",
         pru="Выбрать каталог проекта", prr="Читаемая/записываемая папка", efr="Открывает корень выбранного проекта", fir="—", sor="Нет", dir="—", err="Папка не является проектом"),
    dict(page="Projects", ru="Открыть недавний проект", en="Open Recent Project",
         pe="Open from recent-projects list", pr="Entry available", ef="Loads recent project", fi="—", so="None", di="Missing path", er="Unavailable project", help="projects",
         pru="Открыть из списка недавних", prr="Запись доступна", efr="Загружает недавний проект", fir="—", sor="Нет", dir="Путь отсутствует", err="Проект недоступен"),
    dict(page="Projects", ru="Удалить из списка недавних", en="Remove from Recent List",
         pe="Remove recent-projects entry", pr="Row selected", ef="Updates settings list only", fi="settings", so="None", di="Empty list", er="—", help="projects",
         pru="Удалить из списка недавних", prr="Выбрана строка", efr="Обновляет только список в настройках", fir="настройки", sor="Нет", dir="Список пуст", err="—"),
    dict(page="Projects", ru="Создать проект", en="Create Project",
         pe="Initialize analysis project", pr="Writable parent folder", ef="Writes project metadata", fi="project DB/files", so="None", di="Empty name", er="IO error", help="projects",
         pru="Создать проект анализа", prr="Доступная родительская папка", efr="Записывает метаданные проекта", fir="БД/файлы проекта", sor="Нет", dir="Пустое имя", err="Ошибка ввода-вывода"),
    # Import / Audit / Viewer / Batch (keep essential)
    dict(page="Import", ru="Выбрать файл", en="Select file", pe="Register MAT file", pr="Active project", ef="Sets active MAT", fi="inventory", so="Read-only source", di="No project", er="Forbidden path", help="import",
         pru="Зарегистрировать файл MAT", prr="Активный проект", efr="Назначает активный MAT", fir="инвентарь", sor="Исходник только чтение", dir="Нет проекта", err="Запрещённый путь"),
    dict(page="Import", ru="Выбрать папку", en="Select folder", pe="Register MAT folder", pr="Active project", ef="Lists MAT files", fi="inventory", so="Read-only source", di="No project", er="Empty folder", help="import",
         pru="Зарегистрировать папку MAT", prr="Активный проект", efr="Списывает файлы MAT", fir="инвентарь", sor="Исходник только чтение", dir="Нет проекта", err="Пустая папка"),
    dict(page="Audit", ru="Обновить аудит", en="Refresh audit", pe="Recompute audit cards", pr="Active MAT", ef="Shows readiness/warnings", fi="audit artifacts", so="None", di="No MAT", er="Parse errors", help="audit",
         pru="Пересчитать карточки аудита", prr="Активный MAT", efr="Показывает готовность/предупреждения", fir="артефакты аудита", sor="Нет", dir="Нет MAT", err="Ошибки разбора"),
    dict(page="Viewer", ru="Первый/Пред/След/Последний", en="First/Prev/Next/Last", pe="Frame navigation", pr="Loaded Viewer", ef="Changes frame", fi="—", so="None", di="Not ready", er="Render error", help="viewer",
         pru="Навигация по кадрам", prr="Просмотр ионограмм загружен", efr="Меняет кадр", fir="—", sor="Нет", dir="Не готов", err="Ошибка отрисовки"),
    dict(page="Viewer", ru="−N мин / +N мин", en="−N min / +N min", pe="Time jump", pr="Time mapping available", ef="Jumps by minutes", fi="—", so="None", di="Mapping unavailable", er="Invalid time", help="viewer",
         pru="Прыжок по времени", prr="Доступна привязка времени", efr="Сдвигает на минуты", fir="—", sor="Нет", dir="Привязка недоступна", err="Неверное время"),
    dict(page="Viewer", ru="Пуск / Пауза / Цикл", en="Play / Pause / Loop", pe="Playback", pr="Loaded Viewer", ef="Animates frames", fi="—", so="None", di="Not ready", er="—", help="viewer",
         pru="Воспроизведение", prr="Просмотр ионограмм загружен", efr="Анимирует кадры", fir="—", sor="Нет", dir="Не готов", err="—"),
    dict(page="Viewer", ru="Кэш", en="Cache", pe="Build derived cache", pr="Imported MAT", ef="Builds Zarr cache", fi="cache files", so="None", di="No MAT", er="Disk full", help="viewer",
         pru="Создать производный кэш", prr="Импортированный MAT", efr="Строит Zarr-кэш", fir="файлы кэша", sor="Нет", dir="Нет MAT", err="Диск заполнен"),
    dict(page="Viewer", ru="Контактный лист", en="Contact sheet", pe="Sequence sheet", pr="Cache preferred", ef="Writes sheet PNG", fi="PNG", so="None", di="No frames", er="Render error", help="sequences",
         pru="Лист последовательности", prr="Предпочтителен кэш", efr="Пишет PNG листа", fir="PNG", sor="Нет", dir="Нет кадров", err="Ошибка отрисовки"),
    dict(page="Viewer", ru="Сохранить PNG", en="Save PNG", pe="Export current view", pr="Rendered frame", ef="Writes PNG", fi="PNG", so="None", di="No image", er="IO error", help="viewer",
         pru="Экспорт текущего вида", prr="Кадр отрисован", efr="Пишет PNG", fir="PNG", sor="Нет", dir="Нет изображения", err="Ошибка ввода-вывода"),
    dict(page="Batch", ru="Старт", en="Start", pe="Run selected pipeline", pr="Valid selection", ef="Creates run + predictions", fi="run root JSON", so="None", di="Invalid selection", er="Stage failures", help="batch",
         pru="Запустить выбранный конвейер", prr="Корректный выбор", efr="Создаёт запуск и предсказания", fir="корень запуска JSON", sor="Нет", dir="Неверный выбор", err="Сбои этапов"),
    dict(page="Batch", ru="Пауза / Продолжить / Отмена", en="Pause / Resume / Cancel", pe="Control run", pr="Running batch", ef="Pauses/resumes/cancels", fi="partial run", so="None", di="Not running", er="—", help="batch",
         pru="Управление пакетным анализом", prr="Идёт пакетный анализ", efr="Пауза/продолжение/отмена", fir="частичный запуск", sor="Нет", dir="Не выполняется", err="—"),
    # Results / expert
    dict(page="Results", ru="Экспорт", en="Export", pe="Open report export", pr="last_run_root", ef="Writes reports", fi="HTML/CSV/JSON", so="None", di="No run", er="Export error", help="reports",
         pru="Открыть экспорт отчётов", prr="Есть корень запуска", efr="Пишет отчёты", fir="HTML/CSV/JSON", sor="Нет", dir="Нет запуска", err="Ошибка экспорта"),
    dict(page="Results", ru="Добавить в набор экспертной проверки", en="Add to review dataset", pe="Owner-review label", pr="Selected result row", ef="Saves owner-reviewed label", fi="review_dataset/labels/*.json", so="None", di="No selection / forbidden source", er="Article 3 blocked", help="expert",
         pru="Метка проверки владельцем", prr="Выбрана строка результата", efr="Сохраняет метку владельца", fir="review_dataset/labels/*.json", sor="Нет", dir="Нет выбора / запрещённый источник", err="Блокировка Article 3"),
    dict(page="Results", ru="Морфология (список)", en="Morphology (structured list)", pe="Canonical morphology choice", pr="Expert dialog open", ef="Sets morphology axis", fi="—", so="None", di="—", er="—", help="expert",
         pru="Канонический выбор морфологии", prr="Открыт диалог эксперта", efr="Задаёт ось морфологии", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Помехи (список)", en="Interference (structured list)", pe="Separate interference axis", pr="Expert dialog open", ef="Sets interference", fi="—", so="None", di="—", er="—", help="expert",
         pru="Отдельная ось помех", prr="Открыт диалог эксперта", efr="Задаёт помехи", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Слой", en="Layer", pe="Layer axis selection", pr="Expert dialog open", ef="Sets layer", fi="—", so="None", di="—", er="—", help="expert",
         pru="Выбор слоя", prr="Открыт диалог эксперта", efr="Задаёт слой", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Неоднозначность", en="Ambiguity", pe="Ambiguity axis selection", pr="Expert dialog open", ef="Sets ambiguity", fi="—", so="None", di="—", er="—", help="expert",
         pru="Выбор неоднозначности", prr="Открыт диалог эксперта", efr="Задаёт неоднозначность", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Качество", en="Quality", pe="Quality axis selection", pr="Expert dialog open", ef="Sets quality", fi="—", so="None", di="—", er="—", help="expert",
         pru="Выбор качества", prr="Открыт диалог эксперта", efr="Задаёт качество", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Статус проверки", en="Reviewer status", pe="Unverified / Owner-reviewed / Expert-confirmed", pr="Expert dialog open", ef="Records review state (never auto Expert-confirmed)", fi="—", so="None", di="—", er="—", help="expert",
         pru="Не проверено / владельцем / экспертом", prr="Открыт диалог эксперта", efr="Записывает статус (Expert-confirmed только вручную)", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Обоснование", en="Rationale", pe="Required free-text rationale", pr="Expert dialog open", ef="Required to save", fi="—", so="None", di="—", er="Empty rationale blocked", help="expert",
         pru="Обязательное текстовое обоснование", prr="Открыт диалог эксперта", efr="Нужно для сохранения", fir="—", sor="Нет", dir="—", err="Пустое обоснование запрещено"),
    dict(page="Results", ru="Альтернативы", en="Alternatives", pe="Optional alternative readings", pr="Expert dialog open", ef="Stores alternatives", fi="—", so="None", di="—", er="—", help="expert",
         pru="Необязательные альтернативы", prr="Открыт диалог эксперта", efr="Сохраняет альтернативы", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Results", ru="Сохранить решение эксперта", en="Save expert decision", pe="Persist structured expert/owner decision", pr="Rationale filled", ef="Writes human decision files", fi="human decision files", so="None", di="Empty rationale", er="IO error", help="expert",
         pru="Сохранить структурированное решение", prr="Заполнено обоснование", efr="Пишет файлы решения", fir="файлы решения", sor="Нет", dir="Пустое обоснование", err="Ошибка ввода-вывода"),
    dict(page="Results", ru="Столбцы", en="Columns", pe="Configure visible columns", pr="Results loaded", ef="Rebuilds table columns", fi="—", so="None", di="—", er="—", help="results",
         pru="Настроить видимые столбцы", prr="Результаты загружены", efr="Перестраивает столбцы", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Reports", ru="Экспорт", en="Export", pe="Write bilingual reports", pr="last_run_root", ef="Creates report set", fi="reports/*", so="None", di="No run", er="IO error", help="reports",
         pru="Записать двуязычные отчёты", prr="Есть корень запуска", efr="Создаёт набор отчётов", fir="reports/*", sor="Нет", dir="Нет запуска", err="Ошибка ввода-вывода"),
    # MATLAB Studio
    dict(page="MATLAB Studio", ru="Запустить в MATLAB", en="Run in MATLAB", pe="Execute selected method via configured backend", pr="Backend + script + MAT", ef="Managed job; Studio result tabs", fi="run output folder", so="None if allow_write off", di="No script/backend", er="MATLAB/Octave error", help="matlab",
         pru="Выполнить метод через настроенную исполнительную среду", prr="Исполнительная среда + скрипт + MAT", efr="Управляемый job; вкладки Studio", fir="папка запуска", sor="Нет, если запись выкл.", dir="Нет скрипта/среды", err="Ошибка MATLAB/Octave"),
    dict(page="MATLAB Studio", ru="Остановить", en="Cancel", pe="Cancel running job", pr="Running job", ef="Requests cancel", fi="partial outputs kept", so="None", di="Idle", er="—", help="matlab",
         pru="Отменить выполняемую задачу", prr="Идёт задача", efr="Запрашивает отмену", fir="частичные выходы", sor="Нет", dir="Простой", err="—"),
    dict(page="MATLAB Studio", ru="Проверить код без запуска", en="Check Code Without Running", pe="Editor-structure checks only — does not execute MATLAB", pr="Editor open", ef="Inline validation card", fi="—", so="None", di="—", er="Empty script", help="matlab",
         pru="Проверка структуры редактора — MATLAB не запускается", prr="Редактор открыт", efr="Встроенная карточка проверки", fir="—", sor="Нет", dir="—", err="Пустой скрипт"),
    dict(page="MATLAB Studio", ru="Ожидаемый результат метода", en="Expected Method Output", pe="Declared outputs from method metadata", pr="Script selected", ef="Describes values/features/figures/files", fi="—", so="None", di="—", er="Unknown method", help="matlab",
         pru="Заявленные выходы из метаданных метода", prr="Скрипт выбран", efr="Описывает значения/признаки/рисунки/файлы", fir="—", sor="Нет", dir="—", err="Неизвестный метод"),
    dict(page="MATLAB Studio", ru="Инструменты редактора…", en="Editor Tools…", pe="Format / Save copy / Compare with original menu", pr="Editor open", ef="Opens editor tools menu", fi="—", so="None", di="—", er="—", help="matlab",
         pru="Меню: форматировать / сохранить копию / сравнить с оригиналом", prr="Редактор открыт", efr="Открывает меню инструментов", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="MATLAB Studio", ru="Дополнительно…", en="More Actions…", pe="Secondary result actions menu", pr="Result panel visible", ef="Opens overflow menu", fi="—", so="None", di="—", er="—", help="matlab",
         pru="Меню вторичных действий результата", prr="Панель результатов видима", efr="Открывает меню", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="MATLAB Studio", ru="Значения", en="Values", pe="Show numeric outputs table", pr="Completed run with values", ef="Fills Values tab", fi="—", so="None", di="No values", er="—", help="matlab",
         pru="Таблица числовых выходов", prr="Завершённый запуск со значениями", efr="Заполняет вкладку «Значения»", fir="—", sor="Нет", dir="Нет значений", err="—"),
    dict(page="MATLAB Studio", ru="Рисунки", en="Figures", pe="Show figure thumbnails", pr="Figures created", ef="Shows Figures tab", fi="PNG/etc in run folder", so="None", di="No figures", er="—", help="matlab",
         pru="Миниатюры рисунков", prr="Рисунки созданы", efr="Показывает вкладку «Рисунки»", fir="PNG и др. в папке запуска", sor="Нет", dir="Нет рисунков", err="—"),
    dict(page="MATLAB Studio", ru="Созданные файлы", en="Created Files", pe="List output files with Open", pr="Files created", ef="Fills Created Files tab", fi="listed files", so="None", di="No files", er="—", help="matlab",
         pru="Список выходных файлов с «Открыть»", prr="Файлы созданы", efr="Заполняет вкладку файлов", fir="перечисленные файлы", sor="Нет", dir="Нет файлов", err="—"),
    dict(page="MATLAB Studio", ru="Открыть папку результатов", en="Open Results Folder", pe="Open run folder", pr="work_dir present", ef="Opens folder", fi="—", so="None", di="No work_dir", er="Missing folder", help="matlab",
         pru="Открыть папку запуска", prr="Есть work_dir", efr="Открывает папку", fir="—", sor="Нет", dir="Нет work_dir", err="Папка отсутствует"),
    dict(page="MATLAB Studio", ru="Показать созданные рисунки", en="Show Generated Figures", pe="Focus Figures tab / open images", pr="Figures exist", ef="Navigates to figures", fi="—", so="None", di="No figures", er="—", help="matlab",
         pru="Перейти к рисункам / открыть изображения", prr="Есть рисунки", efr="Переходит к рисункам", fir="—", sor="Нет", dir="Нет рисунков", err="—"),
    dict(page="MATLAB Studio", ru="Экспортировать результат", en="Export Result", pe="Export Studio result package", pr="Result loaded", ef="Writes export", fi="export files", so="None", di="No result", er="IO error", help="matlab",
         pru="Экспорт пакета результата Studio", prr="Результат загружен", efr="Пишет экспорт", fir="файлы экспорта", sor="Нет", dir="Нет результата", err="Ошибка ввода-вывода"),
    dict(page="MATLAB Studio", ru="Добавить в сравнение методов", en="Add to Method Comparison", pe="Hand-off candidates", pr="Candidates present", ef="Prepares comparison payload; not main Results", fi="—", so="None", di="No candidates", er="—", help="compare",
         pru="Передать кандидатов в сравнение", prr="Есть кандидаты", efr="Готовит полезную нагрузку; не основные Результаты", fir="—", sor="Нет", dir="Нет кандидатов", err="—"),
    dict(page="MATLAB Studio", ru="Зарегистрировать как плагин MATLAB", en="Register MATLAB Plugin", pe="Create plugin manifest", pr="Successful complete run", ef="Writes manifest", fi="iml-matlab.yaml", so="None", di="Failed/incomplete run", er="Wizard refuses", help="matlab",
         pru="Создать манифест плагина", prr="Успешный полный запуск", efr="Пишет манифест", fir="iml-matlab.yaml", sor="Нет", dir="Сбой/неполный запуск", err="Мастер отказывает"),
    dict(page="MATLAB Studio", ru="Запустить снова", en="Run Again", pe="Re-submit last method", pr="Prior script context", ef="Starts new managed job", fi="new run folder", so="None", di="No backend", er="MATLAB error", help="matlab",
         pru="Повторно выполнить метод", prr="Есть контекст скрипта", efr="Новый управляемый job", fir="новая папка запуска", sor="Нет", dir="Нет среды", err="Ошибка MATLAB"),
    dict(page="MATLAB Studio", ru="Технический журнал", en="Technical Log", pe="Open Technical Log tab", pr="—", ef="Shows log text", fi="—", so="None", di="—", er="—", help="matlab",
         pru="Открыть вкладку технического журнала", prr="—", efr="Показывает текст журнала", fir="—", sor="Нет", dir="—", err="—"),
    # Pipeline
    dict(page="Pipeline Builder", ru="Проверить", en="Validate", pe="Validate pipeline dependencies", pr="Project open", ef="Shows validation summary", fi="—", so="None", di="—", er="Misconfigured deps", help="pipeline",
         pru="Проверить зависимости конвейера", prr="Проект открыт", efr="Показывает сводку проверки", fir="—", sor="Нет", dir="—", err="Нарушены зависимости"),
    dict(page="Pipeline Builder", ru="Сохранить конвейер", en="Save", pe="Save pipeline for future runs only", pr="Validated/edited pipeline", ef="Writes pipeline config; does not alter existing results", fi="pipeline config", so="None", di="—", er="IO error", help="pipeline",
         pru="Сохранить конвейер только для будущих запусков", prr="Отредактированный конвейер", efr="Пишет конфиг; прошлые результаты не меняет", fir="конфиг конвейера", sor="Нет", dir="—", err="Ошибка ввода-вывода"),
    dict(page="Pipeline Builder", ru="Сохранить как новый", en="Save As", pe="Save as new named pipeline", pr="Edited pipeline", ef="Writes new pipeline definition", fi="pipeline config", so="None", di="—", er="IO error", help="pipeline",
         pru="Сохранить как новый именованный конвейер", prr="Отредактированный конвейер", efr="Пишет новое определение", fir="конфиг конвейера", sor="Нет", dir="—", err="Ошибка ввода-вывода"),
    dict(page="Pipeline Builder", ru="Отменить изменения", en="Revert", pe="Discard unsaved pipeline edits", pr="Unsaved changes", ef="Reloads saved pipeline", fi="—", so="None", di="No unsaved changes", er="—", help="pipeline",
         pru="Отменить несохранённые правки конвейера", prr="Есть несохранённые изменения", efr="Перезагружает сохранённый конвейер", fir="—", sor="Нет", dir="Нет несохранённых", err="—"),
    dict(page="Pipeline Builder", ru="Сравнить с сохранённым", en="Compare with Saved", pe="Diff current vs saved pipeline", pr="Pipeline loaded", ef="Shows change summary", fi="—", so="None", di="—", er="—", help="pipeline",
         pru="Сравнить текущий с сохранённым", prr="Конвейер загружен", efr="Показывает сводку изменений", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Pipeline Builder", ru="Восстановить по умолчанию", en="Restore Defaults", pe="Restore default stage set", pr="Project open", ef="Resets draft (save still required)", fi="—", so="None", di="—", er="—", help="pipeline",
         pru="Восстановить набор этапов по умолчанию", prr="Проект открыт", efr="Сбрасывает черновик (нужно сохранить)", fir="—", sor="Нет", dir="—", err="—"),
    dict(page="Pipeline Builder", ru="Настроить… (этап)", en="Configure… (stage)", pe="Open stage configuration", pr="Stage card selected", ef="Edits stage implementation/options", fi="—", so="None", di="Unavailable stage", er="—", help="pipeline",
         pru="Открыть настройку этапа", prr="Выбрана карточка этапа", efr="Правит реализацию/опции этапа", fir="—", sor="Нет", dir="Недоступный этап", err="—"),
    # Parameters
    dict(page="Parameters", ru="Принять", en="Accept", pe="Accept candidate with provenance", pr="Parameter selected", ef="Stores accepted provenance; may enter reports", fi="parameter decision", so="None", di="No value", er="—", help="parameters",
         pru="Принять кандидата с происхождением", prr="Параметр выбран", efr="Сохраняет происхождение; может попасть в отчёты", fir="решение по параметру", sor="Нет", dir="Нет значения", err="—"),
    dict(page="Parameters", ru="Отклонить", en="Reject", pe="Reject candidate", pr="Parameter selected", ef="Marks rejected", fi="parameter decision", so="None", di="—", er="—", help="parameters",
         pru="Отклонить кандидата", prr="Параметр выбран", efr="Помечает отклонённым", fir="решение по параметру", sor="Нет", dir="—", err="—"),
    dict(page="Parameters", ru="Неопределённо", en="Indeterminate", pe="Mark indeterminate", pr="Parameter selected", ef="Keeps uncertainty", fi="parameter decision", so="None", di="—", er="—", help="parameters",
         pru="Отметить как неопределённое", prr="Параметр выбран", efr="Сохраняет неопределённость", fir="решение по параметру", sor="Нет", dir="—", err="—"),
    dict(page="Parameters", ru="Сохранить решение эксперта", en="Save Expert Edits", pe="Persist parameter expert edits", pr="Edits pending", ef="Writes parameter decisions", fi="parameter files", so="None", di="—", er="IO error", help="parameters",
         pru="Сохранить правки эксперта по параметрам", prr="Есть несохранённые правки", efr="Пишет решения по параметрам", fir="файлы параметров", sor="Нет", dir="—", err="Ошибка ввода-вывода"),
    dict(page="Parameters", ru="Карточка параметра / справка", en="Parameter detail / help", pe="Show full name, meaning, limits, Accept effect", pr="Row selected", ef="Fills detail card", fi="—", so="None", di="—", er="—", help="parameters",
         pru="Полное имя, смысл, ограничения, эффект Accept", prr="Выбрана строка", efr="Заполняет карточку детали", fir="—", sor="Нет", dir="—", err="—"),
    # Model Lab / Settings / Help
    dict(page="Model Lab", ru="Импорт размеченного CSV…", en="Import labeled CSV…", pe="Load training CSV", pr="Valid CSV", ef="Loads dataset", fi="—", so="None", di="Cancel", er="Validation error", help="models",
         pru="Загрузить обучающий CSV", prr="Корректный CSV", efr="Загружает набор", fir="—", sor="Нет", dir="Отмена", err="Ошибка проверки"),
    dict(page="Model Lab", ru="Собрать синтетический набор", en="Build synthetic development set", pe="Create synthetic CSV", pr="Writable model_lab", ef="Writes synthetic_dev.csv", fi="model_lab/datasets", so="None", di="—", er="Feature errors", help="models",
         pru="Создать синтетический CSV", prr="Записываемый model_lab", efr="Пишет synthetic_dev.csv", fir="model_lab/datasets", sor="Нет", dir="—", err="Ошибки признаков"),
    dict(page="Model Lab", ru="Обучить", en="Train", pe="Train development model", pr="Dataset loaded", ef="Writes model card", fi="model_lab models", so="None", di="No dataset", er="Missing values / train error", help="models",
         pru="Обучить разработочную модель", prr="Набор загружен", efr="Пишет карточку модели", fir="модели model_lab", sor="Нет", dir="Нет набора", err="Пропуски значений / ошибка обучения"),
    dict(page="Model Lab", ru="Включить выбранную модель в анализ", en="Enable selected model in analysis", pe="Opt-in ML stage", pr="Selected model + trust", ef="Sets enabled_model_ids", fi="settings", so="None", di="No selection / trust declined", er="Foreign model warning", help="models",
         pru="Опционально включить ML-этап", prr="Модель выбрана + доверие", efr="Задаёт enabled_model_ids", fir="настройки", sor="Нет", dir="Нет выбора / отказ доверия", err="Предупреждение о чужой модели"),
    dict(page="Settings", ru="Сохранить / Сброс", en="Save / Reset", pe="Persist or reload settings", pr="—", ef="Writes settings store", fi="settings file", so="None", di="—", er="IO error", help="settings",
         pru="Сохранить или перезагрузить настройки", prr="—", efr="Пишет хранилище настроек", fir="файл настроек", sor="Нет", dir="—", err="Ошибка ввода-вывода"),
    dict(page="Settings", ru="Язык интерфейса", en="Interface language", pe="Switch EN/RU", pr="—", ef="Retranslates UI", fi="settings", so="None", di="—", er="—", help="settings",
         pru="Переключить EN/RU", prr="—", efr="Переводит интерфейс", fir="настройки", sor="Нет", dir="—", err="—"),
    dict(page="Settings", ru="Масштаб интерфейса", en="Interface scale", pe="UI scale percent", pr="—", ef="Applies scale preference", fi="settings", so="None", di="—", er="—", help="settings",
         pru="Масштаб интерфейса в процентах", prr="—", efr="Применяет масштаб", fir="настройки", sor="Нет", dir="—", err="—"),
    dict(page="Help", ru="Восстановить введения", en="Restore introductions", pe="Restore page intros", pr="—", ef="Shows intro panels", fi="settings", so="None", di="—", er="—", help="help",
         pru="Восстановить введения страниц", prr="—", efr="Показывает панели введения", fir="настройки", sor="Нет", dir="—", err="—"),
]


HEADER_EN = "## Complete control reference (matches UI 1.1.1)\n\n| Page | RU label | EN label | Purpose | Prerequisites | Immediate effect | Files created | Source-data effect | Disabled when | Possible errors | Help topic |\n|------|----------|----------|---------|---------------|------------------|----------------|--------------------|---------------|-----------------|------------|\n"
HEADER_RU = "## Полный справочник элементов управления (соответствует UI 1.1.1)\n\n| Страница | Подпись RU | Подпись EN | Назначение | Предпосылки | Немедленный эффект | Создаваемые файлы | Влияние на исходные данные | Когда отключён | Возможные ошибки | Тема справки |\n|----------|------------|------------|------------|-------------|--------------------|-------------------|----------------------------|----------------|------------------|--------------|\n"
FOOT_EN = "\nScientific status on Results is always one of: Automatic candidate / Owner-reviewed / Expert-confirmed. Default automatic rows must never be read as confirmed classifications.\n"
FOOT_RU = "\nНаучный статус на странице «Результаты»: Автоматический кандидат / Проверено владельцем / Подтверждено экспертом. Автоматические строки нельзя считать подтверждённой классификацией.\n"


def _patch(path: Path, header: str, rows: list[str], foot: str, heading: str) -> int:
    text = path.read_text(encoding="utf-8")
    # Replace from Complete/Полный control heading through the scientific-status paragraph.
    pattern = re.compile(
        r"## (?:Complete control reference|Полный справочник элементов управления).*?(?=\n## |\nHistorical |\nИсторические |\Z)",
        re.S,
    )
    block = header + "".join(rows) + foot
    if not pattern.search(text):
        # Append before end if missing
        text = text.rstrip() + "\n\n" + block
    else:
        text = pattern.sub(block.rstrip() + "\n\n", text, count=1)
    path.write_text(text, encoding="utf-8")
    return len(rows)


def main() -> int:
    en_rows = [
        f"| {c['page']} | {c['ru']} | {c['en']} | {c['pe']} | {c['pr']} | {c['ef']} | {c['fi']} | {c['so']} | {c['di']} | {c['er']} | {c['help']} |\n"
        for c in CONTROLS
    ]
    ru_rows = [
        f"| {c['page']} | {c['ru']} | {c['en']} | {c['pru']} | {c['prr']} | {c['efr']} | {c['fir']} | {c['sor']} | {c['dir']} | {c['err']} | {c['help']} |\n"
        for c in CONTROLS
    ]
    n1 = _patch(ROOT / "docs" / "USER_GUIDE_EN.md", HEADER_EN, en_rows, FOOT_EN, "Complete")
    n2 = _patch(ROOT / "docs" / "USER_GUIDE_RU.md", HEADER_RU, ru_rows, FOOT_RU, "Полный")
    print(f"USER_GUIDE_EN rows={n1}")
    print(f"USER_GUIDE_RU rows={n2}")
    # Emit machine-readable list for validators
    out = ROOT / "docs" / "_control_reference_phase3c.json"
    import json

    out.write_text(
        json.dumps({"count": len(CONTROLS), "en_labels": [c["en"] for c in CONTROLS]}, indent=2),
        encoding="utf-8",
    )
    print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

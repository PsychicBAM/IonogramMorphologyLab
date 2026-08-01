"""Approved bilingual help content (does not index Article 3 blocked paths)."""

from __future__ import annotations

HELP_SECTIONS: list[dict[str, str]] = [
    {
        "id": "quick_start",
        "title_en": "1. Quick Start",
        "title_ru": "1. Быстрый старт",
        "body_en": "Create a project → import a MAT file → audit → select the KFU provisional profile (or wizard) → build cache → open Viewer → choose frames → run batch → review results → export reports. Results are candidate morphology only.",
        "body_ru": "Создайте проект → импортируйте MAT → аудит → выберите провизорный профиль KFU (или мастер) → создайте кэш → откройте просмотр → выберите кадры → пакетный анализ → результаты → экспорт. Результаты — только кандидатная морфология.",
    },
    {
        "id": "project",
        "title_en": "2. Creating a Project",
        "title_ru": "2. Создание проекта",
        "body_en": "A project stores metadata, provenance, runs, and expert decisions in a local workspace. Source MAT files stay outside the project and are never modified.",
        "body_ru": "Проект хранит метаданные, происхождение, запуски и решения эксперта в локальной рабочей области. Исходные MAT остаются вне проекта и не изменяются.",
    },
    {
        "id": "import",
        "title_en": "3. Importing MAT Data",
        "title_ru": "3. Импорт MAT",
        "body_en": "Select a file or folder. Protected Scientific Study mode is optional and off by default; when enabled, it blocks only the paths configured by the user or project. It is not a permanent Article 3 blocklist. Supported: MATLAB v5/v7 (SciPy) and v7.3 (HDF5).",
        "body_ru": "Выберите файл или папку. Режим защищённого научного исследования необязателен и по умолчанию выключен; при включении он блокирует только пути, настроенные пользователем или проектом. Это не постоянный список блокировки Article 3. Поддержка: MATLAB v5/v7 (SciPy) и v7.3 (HDF5).",
    },
    {
        "id": "variables",
        "title_en": "4. Understanding MAT Variables",
        "title_ru": "4. Переменные MAT",
        "body_en": "For the KFU archive the amplitude variable is usually Amp_all with shape 368640×400 (1440 minutes × 256 height bins × 400 frequencies). Filenames may say Am_all.",
        "body_ru": "В архиве KFU амплитуда обычно Amp_all, форма 368640×400 (1440 минут × 256 высот × 400 частот). Имя файла может быть Am_all.",
    },
    {
        "id": "profiles",
        "title_en": "5. Instrument Profiles",
        "title_ru": "5. Профили приборов",
        "body_en": "Profiles define how matrices map to frames, frequency, and nominal virtual height. User-defined profiles are never shown as instrument-verified.",
        "body_ru": "Профиль задаёт соответствие матрицы кадрам, частоте и номинальной виртуальной высоте. Пользовательский профиль никогда не показывается как верифицированный прибором.",
    },
    {
        "id": "kfu_provisional",
        "title_en": "6. Why the KFU Profile Is Provisional",
        "title_ru": "6. Почему профиль KFU провизорный",
        "body_en": "Shape and ff vector are supported by project evidence, but absolute MHz/km metrology and clock confirmation remain open (Gate2). Height is nominal virtual height, not true height.",
        "body_ru": "Форма и вектор ff подтверждены материалами проекта, но абсолютная метрология МГц/км и часы остаются открытыми (Gate2). Высота — номинальная виртуальная, не истинная.",
    },
    {
        "id": "cache",
        "title_en": "7. Building the Cache",
        "title_ru": "7. Создание кэша",
        "body_en": "Large MAT files are converted once to a read-only derived Zarr cache chunked by frame. Cache identity includes source SHA, variable, profile, and format version. The MAT is never overwritten.",
        "body_ru": "Большие MAT один раз преобразуются в производный Zarr-кэш с нарезкой по кадрам. Идентичность кэша включает SHA источника, переменную, профиль и версию формата. MAT не перезаписывается.",
    },
    {
        "id": "viewer",
        "title_en": "8. Viewing Real Ionograms",
        "title_ru": "8. Просмотр реальных ионограмм",
        "body_en": "After import, the Viewer shows real frames. Synthetic demo is a separate teaching mode. Raw view has no hidden smoothing.",
        "body_ru": "После импорта просмотрщик показывает реальные кадры. Синтетика — отдельный учебный режим. Сырой вид без скрытого сглаживания.",
    },
    {
        "id": "frame_time",
        "title_en": "9. Frame Index and Time",
        "title_ru": "9. Индекс кадра и время",
        "body_en": "For KFU, frame 1 ≈ 00:00, frame 1440 ≈ 23:59 provisionally (minute = index−1). This is not metrologically confirmed.",
        "body_ru": "Для KFU кадр 1 ≈ 00:00, кадр 1440 ≈ 23:59 предварительно (минута = индекс−1). Это не метрологически подтверждено.",
    },
    {
        "id": "contact",
        "title_en": "10. Contact Sheets",
        "title_ru": "10. Контактные листы",
        "body_en": "Build 3×3…5×5 grids with chosen minute steps. A summary shows count and time span before rendering.",
        "body_ru": "Сетки 3×3…5×5 с выбранным шагом минут. Перед отрисовкой показывается число кадров и интервал времени.",
    },
    {
        "id": "batch_select",
        "title_en": "11. Batch Selection",
        "title_ru": "11. Выбор кадров",
        "body_en": "Modes: single, frame range, time range, full day, custom list, contact sequence. Always shows why N frames were selected (e.g. step 121 → 12 frames).",
        "body_ru": "Режимы: один кадр, диапазон, время, сутки, список, контактный лист. Всегда объясняется, почему выбрано N кадров (например шаг 121 → 12 кадров).",
    },
    {
        "id": "batch_run",
        "title_en": "12. Batch Analysis",
        "title_ru": "12. Пакетный анализ",
        "body_en": "Choose operations (audit/cache/render/features/rules/export). Pause, resume, cancel. Cancel keeps completed outputs.",
        "body_ru": "Выберите операции (аудит/кэш/рендер/признаки/правила/экспорт). Пауза, продолжение, отмена. Отмена сохраняет уже готовые результаты.",
    },
    {
        "id": "quality",
        "title_en": "13. Data-Quality Statuses",
        "title_ru": "13. Статусы качества",
        "body_en": "valid, valid_with_warning, all_zero, unreadable, CRC_error, unexpected_shape, nonfinite_data, unsupported_profile, insufficient_metadata, not_assessable. Unusual morphology is not treated as corruption.",
        "body_ru": "valid, valid_with_warning, all_zero, unreadable, CRC_error и др. Необычная морфология не считается порчей данных.",
    },
    {
        "id": "categories",
        "title_en": "14. Morphology Categories",
        "title_ru": "14. Категории морфологии",
        "body_en": "Canonical tokens: frequency, range, mixed, none, indeterminate, artifact, not_assessable, other, abstain. Display names are translated; tokens stay English internally.",
        "body_ru": "Канонические значения: frequency, range, mixed, none, indeterminate, artifact, not_assessable, other, abstain. Отображаемые имена переводятся; внутри остаются английские токены.",
    },
    {
        "id": "auto_vs_human",
        "title_en": "15. Candidate Result versus Human Decision",
        "title_ru": "15. Автоматический кандидат и решение эксперта",
        "body_en": "Automatic results are never overwritten by expert edits. Both are stored separately with an audit trail.",
        "body_ru": "Автоматический результат не перезаписывается правкой эксперта. Оба хранятся отдельно с журналом.",
    },
    {
        "id": "confidence",
        "title_en": "16. Confidence and Calibration",
        "title_ru": "16. Уверенность и калибровка",
        "body_en": "If confidence_score is null, the UI explains that model calibration has not been performed. Do not treat status labels as calibrated probabilities.",
        "body_ru": "Если confidence_score отсутствует, интерфейс объясняет, что калибровка модели не выполнена. Статусы — не калиброванные вероятности.",
    },
    {
        "id": "abstention",
        "title_en": "17. Abstention",
        "title_ru": "17. Воздержание алгоритма",
        "body_en": "The algorithm may abstain under O/X ambiguity, disagreement, out-of-domain profile, or poor quality. Abstention is a valid scientific outcome.",
        "body_ru": "Алгоритм может воздержаться при O/X-неоднозначности, разногласиях, вне области профиля или плохом качестве. Воздержание — допустимый научный исход.",
    },
    {
        "id": "alternatives",
        "title_en": "18. Alternative Interpretations",
        "title_ru": "18. Альтернативные трактовки",
        "body_en": "Disagreement engine lists competing interpretations with supporting/opposing evidence and recommended expert action.",
        "body_ru": "Движок разногласий показывает конкурирующие трактовки с доводами «за/против» и рекомендацией эксперту.",
    },
    {
        "id": "ox",
        "title_en": "19. O/X Ambiguity",
        "title_ru": "19. Неоднозначность O/X",
        "body_en": "Two branches do not prove O/X. Amp_all has no polarimetry guarantee. Possible O/X triggers abstention from automatic spread assignment.",
        "body_ru": "Две ветви не доказывают O/X. В Amp_all нет гарантии поляриметрии. Возможная O/X вызывает воздержание от автоматического назначения рассеяния.",
    },
    {
        "id": "interference",
        "title_en": "20. Vertical Interference",
        "title_ru": "20. Вертикальные помехи",
        "body_en": "Vertical stripes can mimic range spread. Interference diagnostics are heuristic; they do not automatically become range morphology.",
        "body_ru": "Вертикальные полосы могут имитировать высотное рассеяние. Диагностика помех эвристическая и не превращается автоматически в range.",
    },
    {
        "id": "atlas",
        "title_en": "21. Reference Atlas",
        "title_ru": "21. Атлас примеров",
        "body_en": "Default install ships metadata citations only. Missing images due to rights are explained, not treated as software errors.",
        "body_ru": "В установке — только метаданные и цитаты. Отсутствие изображений из‑за прав объясняется, а не выглядит как ошибка программы.",
    },
    {
        "id": "science",
        "title_en": "22. Scientific Basis",
        "title_ru": "22. Научная основа",
        "body_en": "Verified formulas and claims with pages; disabled candidates (e.g. unverified Appleton–Hartree) are clearly marked. Engineering metrics are not ionospheric laws.",
        "body_ru": "Проверенные формулы и утверждения со страницами; отключённые кандидаты помечены. Инженерные метрики — не ионосферные законы.",
    },
    {
        "id": "reports",
        "title_en": "23. Reports and Exports",
        "title_ru": "23. Отчёты и экспорт",
        "body_en": "CSV/JSON/HTML/Markdown, bibliography, reproducibility manifest. Reports separate quality, morphology, alternatives, references, limitations, expert decision.",
        "body_ru": "CSV/JSON/HTML/Markdown, библиография, манифест воспроизводимости. Отчёт разделяет качество, морфологию, альтернативы, источники, ограничения, решение эксперта.",
    },
    {
        "id": "settings",
        "title_en": "24. Settings",
        "title_ru": "24. Настройки",
        "body_en": "Tabs: General, Data, Viewer, Performance, Analysis, Reports, Privacy, Advanced. scientific_strict is the recommended default; you may choose another analysis mode and the choice persists.",
        "body_ru": "Вкладки: Общие, Данные, Просмотр, Производительность, Анализ, Отчёты, Конфиденциальность, Дополнительно. scientific_strict — рекомендуемое значение по умолчанию; можно выбрать другой режим анализа, и выбор сохранится.",
    },
    {
        "id": "perf_trouble",
        "title_en": "25. Performance Troubleshooting",
        "title_ru": "25. Ускорение работы",
        "body_en": "Build cache once; use prefetch; prefer Fast Preview for browsing; use Full resolution for final features; reduce workers if RAM is low.",
        "body_ru": "Создайте кэш один раз; включите prefetch; для просмотра — быстрый предпросмотр; для признаков — полное разрешение; уменьшите workers при нехватке RAM.",
    },
    {
        "id": "errors",
        "title_en": "26. Error Troubleshooting",
        "title_ru": "26. Ошибки",
        "body_en": "CRC/unreadable: skip file, continue batch, source unchanged. Cache invalid: rebuild. Profile mismatch: check variable/shape. Blocked path: choose another folder.",
        "body_ru": "CRC/нечитаемый: пропустить файл, продолжить пакет, источник не изменён. Кэш недействителен: пересобрать. Несовпадение профиля: проверить переменную/форму. Блок пути: выбрать другую папку.",
    },
    {
        "id": "limitations",
        "title_en": "27. Scientific Limitations",
        "title_ru": "27. Научные ограничения",
        "body_en": "No validated accuracy claim; no mechanism confirmation from images alone; no dawn/dusk features in morphology; Article 3 labels unused.",
        "body_ru": "Нет заявления о валидированной точности; нет подтверждения механизма только по изображению; нет dawn/dusk признаков в морфологии; метки Article 3 не используются.",
    },
    {
        "id": "glossary",
        "title_en": "28. Glossary",
        "title_ru": "28. Глоссарий",
        "body_en": "Candidate morphology; nominal virtual height; provisional time; abstain; O/X ambiguity; development-calibration threshold; derived diagnostic view; source SHA; FrameStore cache.",
        "body_ru": "Кандидатная морфология; номинальная виртуальная высота; провизорное время; воздержание; O/X-неоднозначность; порог development-calibration; производный диагностический вид; SHA источника; кэш FrameStore.",
    },
    {
        "id": "matlab_studio_overview",
        "title_en": "29. What MATLAB Studio Is",
        "title_ru": "29. Что такое MATLAB Studio",
        "body_en": "MATLAB Studio is a local workspace for importing, documenting, versioning, and optionally executing MATLAB or Octave scripts against derived analysis inputs.",
        "body_ru": "MATLAB Studio — это локальная среда для импорта, документирования, версионирования и необязательного запуска скриптов MATLAB или Octave на производных входных данных анализа.",
    },
    {
        "id": "install_matlab_engine",
        "title_en": "30. Installing MATLAB Engine",
        "title_ru": "30. Установка MATLAB Engine",
        "body_en": "Install MATLAB Engine for Python from your licensed MATLAB installation, then restart IML. Detection reports availability; it does not install MATLAB or transmit credentials.",
        "body_ru": "Установите MATLAB Engine for Python из вашей лицензированной установки MATLAB, затем перезапустите IML. Обнаружение сообщает о доступности, но не устанавливает MATLAB и не передаёт учётные данные.",
    },
    {
        "id": "configure_matlab",
        "title_en": "31. Configuring MATLAB",
        "title_ru": "31. Настройка MATLAB",
        "body_en": "In Settings → MATLAB, select a backend, optionally provide the MATLAB executable, set a timeout, and use a dedicated working directory for generated artifacts.",
        "body_ru": "В Настройки → MATLAB выберите backend, при необходимости укажите исполняемый файл MATLAB, задайте тайм-аут и отдельную рабочую папку для создаваемых артефактов.",
    },
    {
        "id": "configure_octave",
        "title_en": "32. Configuring Octave",
        "title_ru": "32. Настройка Octave",
        "body_en": "Set the Octave executable in Settings → MATLAB. Octave is useful for compatible scripts, but MATLAB toolbox and language compatibility are not complete.",
        "body_ru": "Укажите исполняемый файл Octave в Настройки → MATLAB. Octave полезен для совместимых скриптов, но совместимость с MATLAB и его тулбоксами неполная.",
    },
    {
        "id": "create_matlab_script",
        "title_en": "33. Creating a Script",
        "title_ru": "33. Создание скрипта",
        "body_en": "Create a script in the library, give it an entry point, describe inputs and outputs in its manifest, and test it on synthetic data before research use.",
        "body_ru": "Создайте скрипт в библиотеке, задайте точку входа, опишите входы и выходы в манифесте и проверьте его на синтетических данных до исследовательского применения.",
    },
    {
        "id": "import_m_files",
        "title_en": "34. Importing .m Files",
        "title_ru": "34. Импорт файлов .m",
        "body_en": "Importing copies a .m file into the local script library and records its hash and an initial version. Imported code remains unverified until you assess it.",
        "body_ru": "При импорте файл .m копируется в локальную библиотеку скриптов, записываются его хэш и начальная версия. Импортированный код остаётся непроверенным до вашей оценки.",
    },
    {
        "id": "import_matlab_folder",
        "title_en": "35. Importing a Folder",
        "title_ru": "35. Импорт папки",
        "body_en": "Folder import discovers .m files recursively and stores each script independently. Review duplicate names and dependencies before enabling a plugin.",
        "body_ru": "Импорт папки рекурсивно находит файлы .m и хранит каждый скрипт отдельно. Перед включением плагина проверьте совпадающие имена и зависимости.",
    },
    {
        "id": "script_manifests",
        "title_en": "36. Script Manifests",
        "title_ru": "36. Манифесты скриптов",
        "body_en": "An .iml-matlab.yaml manifest declares the entry point, script type, parameters, expected outputs, timeout, compatibility, rights, and scientific status.",
        "body_ru": "Манифест .iml-matlab.yaml задаёт точку входа, тип скрипта, параметры, ожидаемые выходы, тайм-аут, совместимость, права и научный статус.",
    },
    {
        "id": "matlab_inputs",
        "title_en": "37. Input Variables",
        "title_ru": "37. Входные переменные",
        "body_en": "The bridge can provide the current frame, selected frames, frequency and range axes, profile, metadata, frame IDs, and parameters through MAT and JSON files.",
        "body_ru": "Мост может передавать текущий кадр, выбранные кадры, оси частоты и высоты, профиль, метаданные, идентификаторы кадров и параметры через файлы MAT и JSON.",
    },
    {
        "id": "matlab_outputs",
        "title_en": "38. Output Variables",
        "title_ru": "38. Выходные переменные",
        "body_en": "Scripts may return matrices and write registered features, candidate results, warnings, provenance, figures, and tables into the isolated run workspace.",
        "body_ru": "Скрипты могут возвращать матрицы и записывать зарегистрированные признаки, кандидатные результаты, предупреждения, происхождение, рисунки и таблицы в изолированную рабочую папку запуска.",
    },
    {
        "id": "run_one_frame",
        "title_en": "39. Running on One Frame",
        "title_ru": "39. Запуск на одном кадре",
        "body_en": "Use one-frame execution to validate parameters and outputs. A missing backend returns a no_backend result; it never reports a successful run.",
        "body_ru": "Используйте запуск на одном кадре для проверки параметров и выходов. При отсутствии backend возвращается no_backend; успешный запуск не имитируется.",
    },
    {
        "id": "run_sequence",
        "title_en": "40. Running on a Sequence",
        "title_ru": "40. Запуск на последовательности",
        "body_en": "Sequence execution passes selected frames in order. Treat temporal results as development outputs unless the sequence method has been validated.",
        "body_ru": "Запуск последовательности передаёт выбранные кадры по порядку. Считайте временные результаты разработческими, пока метод последовательности не валидирован.",
    },
    {
        "id": "run_folder",
        "title_en": "41. Running on a Folder",
        "title_ru": "41. Запуск на папке",
        "body_en": "Folder runs should log each source, status, and error independently so a failed file does not hide completed outputs from other files.",
        "body_ru": "Запуски по папке должны независимо журналировать каждый источник, статус и ошибку, чтобы сбой одного файла не скрывал готовые выходы других файлов.",
    },
    {
        "id": "matlab_parameters",
        "title_en": "42. Parameters",
        "title_ru": "42. Параметры",
        "body_en": "Declare parameter names, defaults, ranges, and units in the manifest. Saved run metadata preserves the exact parameter values used.",
        "body_ru": "Объявляйте имена параметров, значения по умолчанию, диапазоны и единицы в манифесте. Метаданные запуска сохраняют точные использованные значения.",
    },
    {
        "id": "execution_logs",
        "title_en": "43. Execution Logs",
        "title_ru": "43. Журналы выполнения",
        "body_en": "Standard output, standard error, diary text, error identifiers, stack traces, elapsed time, backend version, and artifact paths belong to the run record.",
        "body_ru": "Стандартный вывод, ошибки, diary, идентификаторы ошибок, стек, время, версия backend и пути артефактов входят в запись запуска.",
    },
    {
        "id": "figures_tables",
        "title_en": "44. Figures and Tables",
        "title_ru": "44. Рисунки и таблицы",
        "body_en": "Save figures and tables into the run workspace with descriptive names. They are derived artifacts and must not overwrite source MAT data.",
        "body_ru": "Сохраняйте рисунки и таблицы в рабочую папку запуска с понятными именами. Это производные артефакты, и они не должны перезаписывать исходные MAT.",
    },
    {
        "id": "create_plugins",
        "title_en": "45. Creating Plugins",
        "title_ru": "45. Создание плагинов",
        "body_en": "A plugin is a script plus a valid manifest registered for a role. Enabling or disabling it changes registry state, not application source code.",
        "body_ru": "Плагин — это скрипт с корректным манифестом, зарегистрированный для роли. Его включение или отключение меняет состояние реестра, а не исходный код приложения.",
    },
    {
        "id": "script_history",
        "title_en": "46. Version History",
        "title_ru": "46. История версий",
        "body_en": "Every import and save stores a timestamped snapshot with hashes and comments. Compare snapshots before restoring an earlier version.",
        "body_ru": "Каждый импорт и сохранение создаёт снимок с временем, хэшами и комментарием. Сравните снимки перед восстановлением ранней версии.",
    },
    {
        "id": "script_errors",
        "title_en": "47. Script Errors",
        "title_ru": "47. Ошибки скриптов",
        "body_en": "Syntax, missing-function, and runtime errors are reported as errors with diagnostics. Fix the script or manifest; do not infer scientific conclusions from a failed run.",
        "body_ru": "Синтаксические ошибки, отсутствующие функции и ошибки времени выполнения сообщаются с диагностикой. Исправьте скрипт или манифест; не делайте научных выводов из неудачного запуска.",
    },
    {
        "id": "matlab_timeouts",
        "title_en": "48. Timeouts",
        "title_ru": "48. Тайм-ауты",
        "body_en": "Set bounded execution time in Settings or the request. A timeout is recorded explicitly and preserves any completed isolated artifacts for inspection.",
        "body_ru": "Задайте ограниченное время выполнения в Настройках или запросе. Тайм-аут фиксируется явно и сохраняет готовые изолированные артефакты для проверки.",
    },
    {
        "id": "safe_source_handling",
        "title_en": "49. Safe Source-Data Handling",
        "title_ru": "49. Безопасная работа с исходными данными",
        "body_en": "Source MAT files are read-only inputs. Hashes before and after execution verify that a run attempt did not change them; use derived workspaces for outputs.",
        "body_ru": "Исходные MAT — входы только для чтения. Хэши до и после выполнения подтверждают, что попытка запуска их не изменила; для выходов используйте производные рабочие папки.",
    },
    {
        "id": "share_scripts",
        "title_en": "50. Sharing Scripts",
        "title_ru": "50. Обмен скриптами",
        "body_en": "Share scripts with manifests, version history, licenses, citations, and dependency notes. Do not include protected source data or assume another system has the same backend.",
        "body_ru": "Передавайте скрипты вместе с манифестами, историей версий, лицензиями, цитатами и примечаниями о зависимостях. Не включайте защищённые исходные данные и не предполагаете одинаковый backend на другой системе.",
    },
    {
        "id": "teaching_examples",
        "title_en": "51. Teaching Examples",
        "title_ru": "51. Учебные примеры",
        "body_en": "Teaching scripts and synthetic examples illustrate the API and workflow. They are examples, not validation data or evidence of method accuracy.",
        "body_ru": "Учебные скрипты и синтетические примеры иллюстрируют API и процесс. Это примеры, а не данные валидации или доказательство точности метода.",
    },
    {
        "id": "matlab_vs_builtin",
        "title_en": "52. MATLAB versus Built-in Analysis",
        "title_ru": "52. MATLAB и встроенный анализ",
        "body_en": "Built-in analysis is maintained with the application. MATLAB Studio runs separately authored code and labels its verification status; neither replaces expert review.",
        "body_ru": "Встроенный анализ поддерживается приложением. MATLAB Studio запускает отдельно созданный код и показывает его статус верификации; ни один вариант не заменяет экспертную проверку.",
    },
    {
        "id": "reproduce_builtin",
        "title_en": "53. Reproducing a Built-in Method",
        "title_ru": "53. Воспроизведение встроенного метода",
        "body_en": "Start from the documented inputs, parameters, and derived views. Compare outputs on synthetic and representative non-protected data, recording versions and tolerances.",
        "body_ru": "Начните с документированных входов, параметров и производных видов. Сравнивайте выходы на синтетических и репрезентативных незащищённых данных, фиксируя версии и допуски.",
    },
    {
        "id": "custom_classifier",
        "title_en": "54. Creating a Custom Classifier",
        "title_ru": "54. Создание пользовательского классификатора",
        "body_en": "A custom classifier should declare features, classes, split strategy, calibration, abstention, and limitations. Mark it development/research use only until external validation.",
        "body_ru": "Пользовательский классификатор должен объявлять признаки, классы, стратегию разбиения, калибровку, воздержание и ограничения. Помечайте его как development/research use only до внешней валидации.",
    },
    {
        "id": "model_lab_overview",
        "title_en": "55. Model Lab Overview",
        "title_ru": "55. Обзор Model Lab",
        "body_en": "Model Lab imports labeled feature CSV files, trains local development models, groups date splits to prevent neighboring-frame leakage, and writes model cards.",
        "body_ru": "Model Lab импортирует размеченные CSV признаков, обучает локальные разработческие модели, группирует разбиения по датам для предотвращения утечки соседних кадров и создаёт карточки моделей.",
    },
    {
        "id": "protected_study_mode",
        "title_en": "56. Protected Scientific Study Mode",
        "title_ru": "56. Режим защищённого научного исследования",
        "body_en": "This optional mode is off by default. When enabled, it enforces only user- or project-configured path, hash, date, or project-ID protections; ordinary paths remain allowed otherwise.",
        "body_ru": "Этот необязательный режим по умолчанию выключен. При включении он применяет только настроенную пользователем или проектом защиту путей, хэшей, дат или ID проекта; в остальных случаях обычные пути разрешены.",
    },
    {
        "id": "interface_language",
        "title_en": "57. Interface Language Settings",
        "title_ru": "57. Настройки языка интерфейса",
        "body_en": "Choose English or Russian in Settings → General. The setting persists locally and updates translated labels, help titles, and explanatory text.",
        "body_ru": "Выберите английский или русский в Настройки → Общие. Настройка сохраняется локально и обновляет переведённые подписи, заголовки справки и пояснения.",
    },
    {
        "id": "analysis_modes",
        "title_en": "58. Analysis Modes",
        "title_ru": "58. Режимы анализа",
        "body_en": "The recommended default is scientific_strict. You may select fast_preview, standard, scientific_strict, or custom; the selected mode persists and is recorded with runs.",
        "body_ru": "Рекомендуемое значение по умолчанию — scientific_strict. Можно выбрать fast_preview, standard, scientific_strict или custom; выбранный режим сохраняется и фиксируется в запусках.",
    },
    {
        "id": "identifying_e",
        "title_en": "59. Identifying E Candidates",
        "title_ru": "59. Кандидаты слоя E",
        "body_en": "An E-layer candidate is recorded on the layer axis only when the visible trace is compatible with the selected profile and rule evidence. This is not a morphology label, a measurement, or confirmation of a physical layer.",
        "body_ru": "Кандидат слоя E записывается только на оси слоя, когда видимая трасса совместима с выбранным профилем и доказательствами правила. Это не метка морфологии, не измерение и не подтверждение физического слоя.",
    },
    {
        "id": "identifying_es",
        "title_en": "60. Identifying Es Candidates",
        "title_ru": "60. Кандидаты Es",
        "body_en": "An Es candidate denotes a trace compatible with the configured Es rules. Keep the Es layer candidate separate from diffuse or spread morphology; the image alone does not establish formation or mechanism.",
        "body_ru": "Кандидат Es обозначает трассу, совместимую с настроенными правилами Es. Отделяйте кандидат слоя Es от диффузной или spread-морфологии; одно изображение не устанавливает образование или механизм.",
    },
    {
        "id": "es_subtypes",
        "title_en": "61. Es Subtypes",
        "title_ru": "61. Подтипы Es",
        "body_en": "Only entries in ES_SUBTYPE_SOURCE_REGISTRY may be shown as source-traceable subtype terms. The bundled registry has no active invented letter list; do not infer, expand, or assign remembered letter subtypes.",
        "body_ru": "Как прослеживаемые по источнику термины подтипов допускаются только записи из ES_SUBTYPE_SOURCE_REGISTRY. В поставляемом реестре нет активного придуманного списка букв; не выводите, не расширяйте и не присваивайте запомненные буквенные подтипы.",
    },
    {
        "id": "identifying_f1",
        "title_en": "62. Identifying F1 Candidates",
        "title_ru": "62. Кандидаты F1",
        "body_en": "F1 is a candidate layer-axis interpretation based on a separable trace and applicable evidence. It remains indeterminate when profile limits, overlap, or trace quality prevent a defensible separation from F2.",
        "body_ru": "F1 — кандидатная трактовка на оси слоя на основе отделимой трассы и применимых доказательств. Значение остаётся indeterminate, если ограничения профиля, перекрытие или качество трассы не позволяют обоснованно отделить F1 от F2.",
    },
    {
        "id": "identifying_f2",
        "title_en": "63. Identifying F2 Candidates",
        "title_ru": "63. Кандидаты F2",
        "body_en": "F2 is a candidate layer-axis interpretation, not a conclusion about plasma conditions. Any estimated frequency or virtual-height parameter must retain its unit, estimation method, calibration status, and limitation.",
        "body_ru": "F2 — кандидатная трактовка на оси слоя, а не вывод об условиях плазмы. Любой оценённый параметр частоты или виртуальной высоты должен сохранять единицу, метод оценки, статус калибровки и ограничение.",
    },
    {
        "id": "f1_f2_ambiguity",
        "title_en": "64. F1/F2 Ambiguity",
        "title_ru": "64. Неоднозначность F1/F2",
        "body_en": "When the traces cannot be separated reliably, record ambiguity or F_unspecified rather than forcing F1 or F2. This ambiguity is separate from morphology and from possible O/X branch ambiguity.",
        "body_ru": "Если трассы нельзя надёжно разделить, фиксируйте неоднозначность или F_unspecified, а не принудительно F1 или F2. Эта неоднозначность отделена от морфологии и от возможной ветвевой неоднозначности O/X.",
    },
    {
        "id": "spread_f_morphology",
        "title_en": "65. Spread-F Morphology",
        "title_ru": "65. Морфология Spread-F",
        "body_en": "Spread-F terms describe candidate image morphology on the morphology axis. They do not identify a layer, establish a cause, or prove that a visible pattern is Spread-F without applicable evidence and expert review.",
        "body_ru": "Термины Spread-F описывают кандидатную морфологию изображения на оси морфологии. Они не идентифицируют слой, не устанавливают причину и не доказывают Spread-F без применимых доказательств и экспертной проверки.",
    },
    {
        "id": "frequency_spread",
        "title_en": "66. Frequency Spread",
        "title_ru": "66. Частотное рассеяние",
        "body_en": "frequency_spread is a candidate horizontal trace-broadening morphology. It must remain distinct from layer identification, interference, and O/X ambiguity; no causal process is inferred from this token.",
        "body_ru": "frequency_spread — кандидатная морфология горизонтального уширения трассы. Её нужно отделять от идентификации слоя, помех и неоднозначности O/X; из этого токена не выводится причинный процесс.",
    },
    {
        "id": "range_spread",
        "title_en": "67. Range Spread",
        "title_ru": "67. Высотное рассеяние",
        "body_en": "range_spread is a candidate vertical or range-direction diffuseness morphology on a nominal virtual-height display. It is not a true-height measurement and can be contradicted by interference diagnostics.",
        "body_ru": "range_spread — кандидатная морфология вертикальной или высотной диффузности на отображении номинальной виртуальной высоты. Это не измерение истинной высоты и может противоречить диагностике помех.",
    },
    {
        "id": "mixed_spread",
        "title_en": "68. Mixed Spread",
        "title_ru": "68. Смешанное рассеяние",
        "body_en": "mixed_spread is available only when candidate frequency- and range-direction evidence coexist. If either component is not assessable, preserve that uncertainty instead of asserting a mixed morphology.",
        "body_ru": "mixed_spread доступно только при совместном наличии кандидатных признаков частотного и высотного направлений. Если любой компонент неоценим, сохраняйте эту неопределённость вместо утверждения смешанной морфологии.",
    },
    {
        "id": "spread_e",
        "title_en": "69. Spread-E",
        "title_ru": "69. Spread-E",
        "body_en": "A candidate Es layer and a spread-like morphology are stored on separate axes. Their co-occurrence is descriptive only and does not establish a Spread-E subtype, mechanism, or causal relation.",
        "body_ru": "Кандидат слоя Es и spread-подобная морфология хранятся на отдельных осях. Их совместное появление носит только описательный характер и не устанавливает подтип Spread-E, механизм или причинную связь.",
    },
    {
        "id": "ox_ambiguity_v11",
        "title_en": "70. O/X Ambiguity",
        "title_ru": "70. Неоднозначность O/X",
        "body_en": "Possible O/X is an ambiguity-axis candidate, not proof of ordinary and extraordinary modes. It may require abstention from automatic morphology assignment and never converts two visible branches into a causal claim.",
        "body_ru": "Возможная O/X — кандидат на оси неоднозначности, а не доказательство обыкновенной и необыкновенной мод. Она может требовать воздержания от автоматического назначения морфологии и никогда не превращает две видимые ветви в причинное утверждение.",
    },
    {
        "id": "multiple_reflections",
        "title_en": "71. Multiple Reflections",
        "title_ru": "71. Множественные отражения",
        "body_en": "Possible multiple reflection or multi-hop structure is an ambiguity candidate. Record competing interpretations and limitations; do not relabel it as a layer or morphology without independent supporting evidence.",
        "body_ru": "Возможная множественная отражённая или многоскачковая структура — кандидат неоднозначности. Фиксируйте конкурирующие трактовки и ограничения; не переименовывайте её в слой или морфологию без независимых подтверждающих доказательств.",
    },
    {
        "id": "ionospheric_parameters",
        "title_en": "72. Ionospheric Parameters",
        "title_ru": "72. Ионосферные параметры",
        "body_en": "Parameter estimates are image-derived candidates. Each export keeps the value, unit, estimation_method, profile, calibration status, source rule, and limitation; do not describe them as confirmed measurements by default.",
        "body_ru": "Оценки параметров — кандидаты, полученные из изображения. Каждый экспорт сохраняет значение, единицу, estimation_method, профиль, статус калибровки, исходное правило и ограничение; по умолчанию не называйте их подтверждёнными измерениями.",
    },
    {
        "id": "custom_rules",
        "title_en": "73. Custom Rules",
        "title_ru": "73. Пользовательские правила",
        "body_en": "Rule Builder creates local, versioned candidate rules. Define one target axis, conditions, outputs, applicability, exclusions, limitations, and abstention; a custom rule is not validated merely because it executes.",
        "body_ru": "Rule Builder создаёт локальные версионированные кандидатные правила. Задайте одну целевую ось, условия, выходы, применимость, исключения, ограничения и воздержание; пользовательское правило не становится валидированным только потому, что выполняется.",
    },
    {
        "id": "rule_sources",
        "title_en": "74. Rule Sources",
        "title_ru": "74. Источники правил",
        "body_en": "Attach source IDs, printed/PDF pages, quoted wording, and rights notes where available. Missing source metadata must stay visible and must not be replaced by remembered terminology or unstated thresholds.",
        "body_ru": "При наличии прикрепляйте ID источника, печатные/PDF-страницы, цитируемую формулировку и сведения о правах. Отсутствующие метаданные источника должны оставаться видимыми и не заменяться запомненной терминологией или неявными порогами.",
    },
    {
        "id": "rule_verification",
        "title_en": "75. Rule Verification",
        "title_ru": "75. Верификация правил",
        "body_en": "Verification status reports documentary and review state, not physical truth. Check source wording, domain, profile compatibility, thresholds, limitations, and an expert review record before changing a status.",
        "body_ru": "Статус верификации сообщает о документальном состоянии и рецензировании, а не о физической истинности. Перед сменой статуса проверьте формулировку источника, область, совместимость профиля, пороги, ограничения и запись экспертной проверки.",
    },
    {
        "id": "rule_testing",
        "title_en": "76. Rule Testing",
        "title_ru": "76. Тестирование правил",
        "body_en": "Use threshold sweeps and labelled comparison to inspect rule behavior. Synthetic frames are teaching/development inputs, not scientific validation evidence; record their status explicitly in test reports.",
        "body_ru": "Используйте перебор порогов и сравнение с разметкой для проверки поведения правила. Синтетические кадры — учебные/разработческие входы, а не доказательство научной валидации; явно фиксируйте их статус в отчётах теста.",
    },
    {
        "id": "rule_packs",
        "title_en": "77. Rule Packs",
        "title_ru": "77. Пакеты правил",
        "body_en": "A rule pack contains a manifest, rules, source context, and documentation. Validate a pack before installing it; a broken or unsafe archive is isolated and does not alter the installed pack library.",
        "body_ru": "Пакет правил содержит манифест, правила, контекст источников и документацию. Проверяйте пакет перед установкой; повреждённый или небезопасный архив изолируется и не меняет установленную библиотеку пакетов.",
    },
    {
        "id": "editing_builtin_matlab",
        "title_en": "78. Editing Built-in MATLAB Methods",
        "title_ru": "78. Редактирование встроенных методов MATLAB",
        "body_en": "Files under matlab_builtin/ are read-only reference methods. Create an editable copy in the user or project library; preserve provenance and do not promote a modified copy to source-verified status without review.",
        "body_ru": "Файлы в matlab_builtin/ — эталонные методы только для чтения. Создавайте редактируемую копию в пользовательской или проектной библиотеке; сохраняйте происхождение и не повышайте изменённую копию до source-verified без проверки.",
    },
    {
        "id": "creating_matlab_detector",
        "title_en": "79. Creating a MATLAB Detector",
        "title_ru": "79. Создание детектора MATLAB",
        "body_en": "Declare a detector entry point, inputs, outputs, parameters, applicability, limitations, and candidate-only wording in its manifest. Test execution separately from scientific validation and keep source MAT inputs read-only.",
        "body_ru": "Объявите в манифесте точку входа детектора, входы, выходы, параметры, применимость, ограничения и формулировки только для кандидатов. Отделяйте тест выполнения от научной валидации и сохраняйте исходные MAT только для чтения.",
    },
    {
        "id": "comparing_methods",
        "title_en": "80. Comparing Methods",
        "title_ru": "80. Сравнение методов",
        "body_en": "Compare methods by documented inputs, profile domain, candidate outputs, disagreements, and limitations. Agreement does not validate a method, and disagreement should remain visible for expert review.",
        "body_ru": "Сравнивайте методы по документированным входам, области профиля, кандидатным выходам, разногласиям и ограничениям. Согласие не валидирует метод, а разногласие должно оставаться видимым для экспертной проверки.",
    },
    {
        "id": "recommended_workflow",
        "title_en": "81. Recommended Workflow",
        "title_ru": "81. Рекомендуемый порядок работы",
        "body_en": (
            "Purpose: remove guesswork about menu order.\n"
            "When: every new project and every return to unfinished work.\n"
            "Steps: (1) create/open project (2) import MAT (3) confirm instrument profile "
            "(4) audit and build cache (5) view ionograms (6) select frames/interval "
            "(7) choose pipeline (8) run analysis (9) inspect results (10) expert decisions "
            "(11) export report.\n"
            "Home shows completed / current / blocked / optional states. Click a step to open its page.\n"
            "Example: no project → Create a project; analysis done → Review results.\n"
            "Common mistakes: opening Viewer before cache; treating optional expert step as required.\n"
            "Troubleshooting: if a step is blocked, complete the previous required step.\n"
            "Limitations: workflow tracks project readiness, not scientific correctness.\n"
            "Related: Quick Start, Projects, UX modes."
        ),
        "body_ru": (
            "Назначение: убрать угадывание порядка меню.\n"
            "Когда: каждый новый проект и возврат к незавершённой работе.\n"
            "Шаги: (1) создать/открыть проект (2) импорт MAT (3) подтвердить профиль "
            "(4) аудит и кэш (5) просмотр (6) выбор кадров (7) конвейер (8) анализ "
            "(9) результаты (10) эксперт (11) отчёт.\n"
            "На Главной видны статусы: выполнен / текущий / заблокирован / необязателен.\n"
            "Пример: нет проекта → Создать проект; анализ готов → Проверить результаты.\n"
            "Ошибки: открытие просмотра до кэша; путаница обязательных и необязательных шагов.\n"
            "Ограничение: порядок отражает готовность проекта, не научную истинность.\n"
            "Связано: Быстрый старт, Проекты, режимы интерфейса."
        ),
    },
    {
        "id": "ux_modes",
        "title_en": "82. Guided / Research / Expert Modes",
        "title_ru": "82. Режимы Guided / Research / Expert",
        "body_en": (
            "Purpose: control interface complexity only.\n"
            "Guided: explanations visible, advanced collapsed, safe defaults, confirmation summaries.\n"
            "Research: full workflow, provenance visible, advanced available but collapsed.\n"
            "Expert: direct access to pipeline internals, rule packs, MATLAB plugins, technical records.\n"
            "Important: changing UX mode never silently changes scientific thresholds or analysis mode.\n"
            "Analysis mode (Fast Preview / Standard / Scientific Strict / Custom) is a separate Settings control.\n"
            "Related: Settings, Recommended workflow, Rule Builder."
        ),
        "body_ru": (
            "Назначение: управлять только сложностью интерфейса.\n"
            "Guided: пояснения видны, advanced свёрнут, безопасные значения по умолчанию.\n"
            "Research: полный рабочий процесс, происхождение видно, advanced доступен, но свёрнут.\n"
            "Expert: прямой доступ к внутренностям конвейера, пакетам правил, MATLAB, техзаписям.\n"
            "Важно: смена UX-режима никогда не меняет научные пороги молча.\n"
            "Режим анализа (Fast Preview / Standard / Scientific Strict / Custom) настраивается отдельно.\n"
            "Связано: Настройки, Рекомендуемый порядок, Rule Builder."
        ),
    },
    {
        "id": "rules_nocode",
        "title_en": "83. Creating a Rule Without Programming",
        "title_ru": "83. Создание правила без программирования",
        "body_en": (
            "Purpose: create candidate scientific rules without Python or MATLAB.\n"
            "Banner: “No programming is required to create a rule.”\n"
            "Wizard steps: purpose → proposed result → conditions → exclusions → Source Assistant → "
            "threshold origin → natural-language preview (EN/RU) → test → save.\n"
            "Built-in examples are templates: copy to draft; originals are not editable.\n"
            "Incomplete source may only be draft / imported_unverified / development — never silently source-verified.\n"
            "Advanced tab may show generated Python/MATLAB/JSON; it is optional.\n"
            "Common mistakes: editing built-in examples in place; claiming source_verified without DOI/page; "
            "confusing UX Expert mode with scientific validation.\n"
            "Related: Rule Testing Lab, Rule packs, Scientific limitations."
        ),
        "body_ru": (
            "Назначение: создавать кандидатные научные правила без Python и MATLAB.\n"
            "Баннер: «Для создания правила программирование не требуется.»\n"
            "Шаги мастера: цель → результат → условия → исключения → ассистент источника → "
            "происхождение порога → предпросмотр (RU/EN) → тест → сохранение.\n"
            "Встроенные примеры — шаблоны: копируйте в черновик; оригиналы не редактируются.\n"
            "Неполный источник допускается только как draft / imported_unverified / development — "
            "никогда не помечается source-verified молча.\n"
            "Вкладка Advanced показывает сгенерированный код по желанию.\n"
            "Ошибки: правка встроенных примеров; source_verified без DOI/страницы; путаница Expert и валидации.\n"
            "Связано: Rule Testing Lab, пакеты правил, научные ограничения."
        ),
    },
    {
        "id": "recovery",
        "title_en": "84. Crash Recovery and Interrupted Runs",
        "title_ru": "84. Восстановление после сбоя",
        "body_en": (
            "Purpose: resume safely after the application closes during processing.\n"
            "Source MAT remains read-only; incomplete runs stay in the project run folder with provenance.\n"
            "Next action: reopen the project from Home → check unfinished operations → re-run only derived steps.\n"
            "If the cache was deleted externally, rebuild cache; if the source hash changed, re-import/audit.\n"
            "Related: Troubleshooting, Projects, Cache."
        ),
        "body_ru": (
            "Назначение: безопасно продолжить работу после закрытия во время обработки.\n"
            "Исходный MAT остаётся только для чтения; незавершённые запуски сохраняются в папке проекта.\n"
            "Действие: откройте проект на Главной → проверьте незавершённые операции → повторите только производные шаги.\n"
            "Если кэш удалён — пересоздайте; если изменился SHA источника — повторите импорт/аудит.\n"
            "Связано: Устранение неисправностей, Проекты, Кэш."
        ),
    },
    {
        "id": "matlab_studio",
        "title_en": "85. MATLAB Studio Overview",
        "title_ru": "85. Обзор MATLAB Studio",
        "body_en": (
            "Purpose: edit and run teaching/research MATLAB methods against the current frame with isolation.\n"
            "Backends: external MATLAB (-batch), optional Engine, optional Octave; core app works without MATLAB.\n"
            "Built-in library methods are ASCII-safe for older MATLAB releases; copy before editing.\n"
            "Errors in user scripts must not crash the GUI; diary and outputs are captured per run.\n"
            "Related: Built-in methods, Plugin guide, Troubleshooting (MATLAB not detected)."
        ),
        "body_ru": (
            "Назначение: редактировать и запускать MATLAB-методы на текущем кадре в изоляции.\n"
            "Бэкенды: внешний MATLAB (-batch), опционально Engine и Octave; ядро работает без MATLAB.\n"
            "Встроенные методы приведены к ASCII для старых релизов; перед правкой создайте копию.\n"
            "Ошибка скрипта не должна ронять GUI; дневник и выходы сохраняются по запуску.\n"
            "Связано: встроенные методы, плагины, устранение неисправностей."
        ),
    },
    {
        "id": "performance",
        "title_en": "86. Performance and Cache Speed",
        "title_ru": "86. Производительность и скорость кэша",
        "body_en": (
            "If the application feels slow: build the frame cache once, enable prefetch, reduce contact-sheet size, "
            "use Fast Preview only for navigation (not for final scientific claims), and keep the cache on a fast local disk.\n"
            "Worker count and RAM limits are in Settings → Performance.\n"
            "Related: Cache, Viewer, Troubleshooting."
        ),
        "body_ru": (
            "Если медленно: один раз создайте кэш кадров, включите prefetch, уменьшите контактный лист, "
            "Fast Preview используйте только для навигации, храните кэш на быстром локальном диске.\n"
            "Число воркеров и лимит RAM — в Настройках → Производительность.\n"
            "Связано: Кэш, Просмотр, Устранение неисправностей."
        ),
    },
]


def help_section_ids() -> list[str]:
    return [s["id"] for s in HELP_SECTIONS]


def get_help_section(section_id: str) -> dict[str, str] | None:
    for s in HELP_SECTIONS:
        if s["id"] == section_id:
            return s
    return None


# Synonyms / colloquial queries → help section ids (RU + EN)
HELP_SYNONYMS: dict[str, list[str]] = {
    "своё правило": ["rules_nocode", "rule_builder", "rules"],
    "свое правило": ["rules_nocode", "rule_builder", "rules"],
    "своё": ["rules_nocode", "rule_builder"],
    "custom rule": ["rules_nocode", "rule_builder", "rules"],
    "rule builder": ["rules_nocode", "rule_builder", "rules"],
    "без кода": ["rules_nocode", "rule_builder"],
    "no code": ["rules_nocode", "rule_builder"],
    "matlab код": ["matlab_studio", "matlab", "matlab_api"],
    "matlab code": ["matlab_studio", "matlab", "matlab_api"],
    "медленно": ["cache", "performance", "troubleshooting"],
    "slow": ["cache", "performance", "troubleshooting"],
    "ионограмма одна": ["viewer", "frame", "time_mapping", "batch"],
    "один кадр": ["viewer", "frame"],
    "single frame": ["viewer", "frame", "batch"],
    "o/x": ["ox", "ambiguity", "branches", "comparing_methods"],
    "o-x": ["ox", "ambiguity", "branches"],
    "неоднозначность": ["ambiguity", "ox", "branches"],
    "workflow": ["quick_start", "project", "recommended_workflow"],
    "с чего начать": ["quick_start", "recommended_workflow", "first_launch"],
    "где начать": ["quick_start", "recommended_workflow"],
    "guided": ["ux_modes", "quick_start"],
    "режим": ["ux_modes", "analysis_modes"],
    "crash": ["troubleshooting", "recovery"],
    "восстановление": ["troubleshooting", "recovery"],
}


def search_help(query: str, lang: str = "en") -> list[dict[str, str]]:
    q = (query or "").strip().lower()
    if not q:
        return list(HELP_SECTIONS)
    by_id = {s["id"]: s for s in HELP_SECTIONS}
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(section: dict[str, str]) -> None:
        sid = section["id"]
        if sid not in seen:
            seen.add(sid)
            found.append(section)

    for phrase, ids in HELP_SYNONYMS.items():
        if phrase in q or q in phrase:
            for sid in ids:
                if sid in by_id:
                    add(by_id[sid])
                else:
                    # fuzzy: any section whose id contains token
                    for s in HELP_SECTIONS:
                        if sid in s["id"] or sid.replace("_", "") in s["id"].replace("_", ""):
                            add(s)

    title = "title_ru" if lang == "ru" else "title_en"
    body = "body_ru" if lang == "ru" else "body_en"
    for s in HELP_SECTIONS:
        if q in s[title].lower() or q in s[body].lower() or q in s["id"]:
            add(s)
    return found

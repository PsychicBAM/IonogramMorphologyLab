# User Guide (EN) — Ionogram Morphology Lab 1.1.1

## Start safely

1. Launch `IonogramMorphologyLab.exe` (portable release) or the development entry point.
2. Choose English or Russian on first launch (change later in **Settings → General → Interface language**).
3. Create a project in a writable workspace. Keep it outside the portable-install folder. Prefer a dedicated drive or folder of your choice (**Settings → Storage**).
4. Begin with the teaching files in [`synthetic_data/`](../synthetic_data/) before using research data.

## Projects page

The **Projects** page has three sections:

1. **Current project** — name, path, creation date, last opened, active source file, active run, unsaved changes.
2. **Open project** — **Open Project**, **Choose Project Folder**, **Open Recent Project**, recent list with availability, **Open**, and **Remove from recent list**.
3. **Create project** — create a new analysis project in a writable parent folder.

Before switching projects the application asks about unsaved edits, stops or resolves active jobs, and clears stale UI state so results from two projects are never mixed.

## Recommended workflow

1. **Import Data** — select a MAT file or folder; IML does not overwrite source MAT data.
2. **Data Audit** — review variables, dimensions, timestamps, and warnings.
3. **Instrument Profile** — select a documented profile or create one; keep provisional metadata marked provisional.
4. **Viewer** — inspect frames and build only the derived cache when needed. Status shows frame X of N and cache readiness.
5. **Batch Analysis** — choose what to analyse (current frame, range, time range, every N minutes, entire file, or custom list), review the confirmation summary, then start. Start stays disabled until the selection is valid.
6. **Results** — read the translated morphology and evidence panel (supporting/contradicting features, rules fired, alternatives, limitations). Canonical tokens stay under **Technical details**.
7. **Expert Review** — record Accept, Change, Indeterminate, or N/A with rationale.
8. **Reports → Export** — review provenance and local paths before sharing EN/RU outputs.

## Batch example

Analyse frames from **05:00 to 07:00 every 10 minutes**:

1. Open **Batch Analysis**.
2. Choose **Every N minutes** (or **Time range** with interval 10).
3. Set start **05:00**, end **07:00**, interval **10**.
4. Choose preset **Standard analysis**.
5. Confirm the summary (MAT, profile, frame count, stages, output folder).
6. Start, then open **Results**.

## Storage

**Settings → Storage** lets you choose project, workspace, cache, reports, models, MATLAB workspace, and temporary folders. Actions:

- Browse / Open folder
- Migrate cache (with rollback on failure)
- Clear cache (never deletes source MAT)
- Restore storage defaults

## Desktop shortcut

Use **Settings → Create Desktop Shortcut** (confirmation required). No administrator rights are needed. The shortcut targets the portable EXE when present and uses the application icon.

## Navigation modes

- **Guided** — Start, Data, Analysis, Reports, Settings, Help
- **Research** — scientific workflow; Methods group collapsed
- **Expert** — all sections

UX mode changes visibility only; it never changes scientific results.

## Important boundaries

- Results are **candidate morphology**, not proof of a physical mechanism or calibrated measurement.
- Source data remains read-only; caches and reports are derived artifacts.
- Rules, MATLAB scripts, and models need independent, domain-appropriate validation.
- Use **Indeterminate** or abstention when evidence is insufficient.
- Canonical non-spread token: serialized `clean` (“No visible spread”).

## Specialized references

- [Installation](INSTALLATION_EN.md)
- [Troubleshooting](TROUBLESHOOTING_EN.md)
- [FAQ](FAQ_EN.md)
- [Data formats](DATA_FORMATS.md)
- [Rule Builder](CUSTOM_RULE_BUILDER_EN.md) and [Rule Testing](RULE_TESTING_GUIDE_EN.md)
- [MATLAB Studio](MATLAB_STUDIO_GUIDE_EN.md)
- [Scientific Guide](SCIENTIFIC_GUIDE_EN.md)
- [Security and Trust](SECURITY_AND_TRUST.md)

Historical full tutorials (archived): [Quick start](archive/user-guides/QUICK_START_EN.md), [Complete user manual](archive/user-guides/COMPLETE_USER_MANUAL_EN.md).

## Complete control reference (matches UI 1.1.1)

| Page | RU label | EN label | Purpose | Prerequisites | Immediate effect | Files created | Source-data effect | Disabled when | Possible errors | Help topic |
|------|----------|----------|---------|---------------|------------------|----------------|--------------------|---------------|-----------------|------------|
| Home | Продолжить рекомендуемый шаг | Continue recommended step | Open next guided page | Project/workflow state | Navigates | — | None | When no next step | Missing project | home |
| Home | Новый проект | New Project | Create project | Writable workspace | Creates project | project dir | None | Invalid path | Permission error | projects |
| Projects | Открыть проект | Open Project | Open existing project file/folder | Valid project on disk | Loads project; clears stale UI | — | None | Active unresolved job without confirm | Invalid project / IO error | projects |
| Projects | Выбрать папку проекта | Choose Project Folder | Browse to a project directory | Writable/readable folder | Opens selected project root | — | None | — | Folder not a project | projects |
| Projects | Открыть недавний проект | Open Recent Project | Open from recent-projects list | Entry available | Loads recent project | — | None | Missing path | Unavailable project | projects |
| Projects | Удалить из списка недавних | Remove from Recent List | Remove recent-projects entry | Row selected | Updates settings list only | settings | None | Empty list | — | projects |
| Projects | Создать проект | Create Project | Initialize analysis project | Writable parent folder | Writes project metadata | project DB/files | None | Empty name | IO error | projects |
| Import | Выбрать файл | Select file | Register MAT file | Active project | Sets active MAT | inventory | Read-only source | No project | Forbidden path | import |
| Import | Выбрать папку | Select folder | Register MAT folder | Active project | Lists MAT files | inventory | Read-only source | No project | Empty folder | import |
| Audit | Обновить аудит | Refresh audit | Recompute audit cards | Active MAT | Shows readiness/warnings | audit artifacts | None | No MAT | Parse errors | audit |
| Viewer | Первый/Пред/След/Последний | First/Prev/Next/Last | Frame navigation | Loaded Viewer | Changes frame | — | None | Not ready | Render error | viewer |
| Viewer | −N мин / +N мин | −N min / +N min | Time jump | Time mapping available | Jumps by minutes | — | None | Mapping unavailable | Invalid time | viewer |
| Viewer | Пуск / Пауза / Цикл | Play / Pause / Loop | Playback | Loaded Viewer | Animates frames | — | None | Not ready | — | viewer |
| Viewer | Кэш | Cache | Build derived cache | Imported MAT | Builds Zarr cache | cache files | None | No MAT | Disk full | viewer |
| Viewer | Контактный лист | Contact sheet | Sequence sheet | Cache preferred | Writes sheet PNG | PNG | None | No frames | Render error | sequences |
| Viewer | Сохранить PNG | Save PNG | Export current view | Rendered frame | Writes PNG | PNG | None | No image | IO error | viewer |
| Batch | Старт | Start | Run selected pipeline | Valid selection | Creates run + predictions | run root JSON | None | Invalid selection | Stage failures | batch |
| Batch | Пауза / Продолжить / Отмена | Pause / Resume / Cancel | Control run | Running batch | Pauses/resumes/cancels | partial run | None | Not running | — | batch |
| Results | Экспорт | Export | Open report export | last_run_root | Writes reports | HTML/CSV/JSON | None | No run | Export error | reports |
| Results | Добавить в набор экспертной проверки | Add to review dataset | Owner-review label | Selected result row | Saves owner-reviewed label | review_dataset/labels/*.json | None | No selection / forbidden source | Article 3 blocked | expert |
| Results | Морфология (список) | Morphology (structured list) | Canonical morphology choice | Expert dialog open | Sets morphology axis | — | None | — | — | expert |
| Results | Помехи (список) | Interference (structured list) | Separate interference axis | Expert dialog open | Sets interference | — | None | — | — | expert |
| Results | Слой | Layer | Layer axis selection | Expert dialog open | Sets layer | — | None | — | — | expert |
| Results | Неоднозначность | Ambiguity | Ambiguity axis selection | Expert dialog open | Sets ambiguity | — | None | — | — | expert |
| Results | Качество | Quality | Quality axis selection | Expert dialog open | Sets quality | — | None | — | — | expert |
| Results | Статус проверки | Reviewer status | Unverified / Owner-reviewed / Expert-confirmed | Expert dialog open | Records review state (never auto Expert-confirmed) | — | None | — | — | expert |
| Results | Обоснование | Rationale | Required free-text rationale | Expert dialog open | Required to save | — | None | — | Empty rationale blocked | expert |
| Results | Альтернативы | Alternatives | Optional alternative readings | Expert dialog open | Stores alternatives | — | None | — | — | expert |
| Results | Сохранить решение эксперта | Save expert decision | Persist structured expert/owner decision | Rationale filled | Writes human decision files | human decision files | None | Empty rationale | IO error | expert |
| Results | Столбцы | Columns | Configure visible columns | Results loaded | Rebuilds table columns | — | None | — | — | results |
| Reports | Экспорт | Export | Write bilingual reports | last_run_root | Creates report set | reports/* | None | No run | IO error | reports |
| MATLAB Studio | Запустить в MATLAB | Run in MATLAB | Execute selected method via configured backend | Backend + script + MAT | Managed job; Studio result tabs | run output folder | None if allow_write off | No script/backend | MATLAB/Octave error | matlab |
| MATLAB Studio | Остановить | Cancel | Cancel running job | Running job | Requests cancel | partial outputs kept | None | Idle | — | matlab |
| MATLAB Studio | Проверить код без запуска | Check Code Without Running | Editor-structure checks only — does not execute MATLAB | Editor open | Inline validation card | — | None | — | Empty script | matlab |
| MATLAB Studio | Ожидаемый результат метода | Expected Method Output | Declared outputs from method metadata | Script selected | Describes values/features/figures/files | — | None | — | Unknown method | matlab |
| MATLAB Studio | Инструменты редактора… | Editor Tools… | Format / Save copy / Compare with original menu | Editor open | Opens editor tools menu | — | None | — | — | matlab |
| MATLAB Studio | Дополнительно… | More Actions… | Secondary result actions menu | Result panel visible | Opens overflow menu | — | None | — | — | matlab |
| MATLAB Studio | Значения | Values | Show numeric outputs table | Completed run with values | Fills Values tab | — | None | No values | — | matlab |
| MATLAB Studio | Рисунки | Figures | Show figure thumbnails | Figures created | Shows Figures tab | PNG/etc in run folder | None | No figures | — | matlab |
| MATLAB Studio | Созданные файлы | Created Files | List output files with Open | Files created | Fills Created Files tab | listed files | None | No files | — | matlab |
| MATLAB Studio | Открыть папку результатов | Open Results Folder | Open run folder | work_dir present | Opens folder | — | None | No work_dir | Missing folder | matlab |
| MATLAB Studio | Показать созданные рисунки | Show Generated Figures | Focus Figures tab / open images | Figures exist | Navigates to figures | — | None | No figures | — | matlab |
| MATLAB Studio | Экспортировать результат | Export Result | Export Studio result package | Result loaded | Writes export | export files | None | No result | IO error | matlab |
| MATLAB Studio | Добавить в сравнение методов | Add to Method Comparison | Hand-off candidates | Candidates present | Prepares comparison payload; not main Results | — | None | No candidates | — | compare |
| MATLAB Studio | Зарегистрировать как плагин MATLAB | Register MATLAB Plugin | Create plugin manifest | Successful complete run | Writes manifest | iml-matlab.yaml | None | Failed/incomplete run | Wizard refuses | matlab |
| MATLAB Studio | Запустить снова | Run Again | Re-submit last method | Prior script context | Starts new managed job | new run folder | None | No backend | MATLAB error | matlab |
| MATLAB Studio | Технический журнал | Technical Log | Open Technical Log tab | — | Shows log text | — | None | — | — | matlab |
| Pipeline Builder | Проверить | Validate | Validate pipeline dependencies | Project open | Shows validation summary | — | None | — | Misconfigured deps | pipeline |
| Pipeline Builder | Сохранить конвейер | Save | Save pipeline for future runs only | Validated/edited pipeline | Writes pipeline config; does not alter existing results | pipeline config | None | — | IO error | pipeline |
| Pipeline Builder | Сохранить как новый | Save As | Save as new named pipeline | Edited pipeline | Writes new pipeline definition | pipeline config | None | — | IO error | pipeline |
| Pipeline Builder | Отменить изменения | Revert | Discard unsaved pipeline edits | Unsaved changes | Reloads saved pipeline | — | None | No unsaved changes | — | pipeline |
| Pipeline Builder | Сравнить с сохранённым | Compare with Saved | Diff current vs saved pipeline | Pipeline loaded | Shows change summary | — | None | — | — | pipeline |
| Pipeline Builder | Восстановить по умолчанию | Restore Defaults | Restore default stage set | Project open | Resets draft (save still required) | — | None | — | — | pipeline |
| Pipeline Builder | Настроить… (этап) | Configure… (stage) | Open stage configuration | Stage card selected | Edits stage implementation/options | — | None | Unavailable stage | — | pipeline |
| Parameters | Принять | Accept | Accept candidate with provenance | Parameter selected | Stores accepted provenance; may enter reports | parameter decision | None | No value | — | parameters |
| Parameters | Отклонить | Reject | Reject candidate | Parameter selected | Marks rejected | parameter decision | None | — | — | parameters |
| Parameters | Неопределённо | Indeterminate | Mark indeterminate | Parameter selected | Keeps uncertainty | parameter decision | None | — | — | parameters |
| Parameters | Сохранить решение эксперта | Save Expert Edits | Persist parameter expert edits | Edits pending | Writes parameter decisions | parameter files | None | — | IO error | parameters |
| Parameters | Карточка параметра / справка | Parameter detail / help | Show full name, meaning, limits, Accept effect | Row selected | Fills detail card | — | None | — | — | parameters |
| Model Lab | Импорт размеченного CSV… | Import labeled CSV… | Load training CSV | Valid CSV | Loads dataset | — | None | Cancel | Validation error | models |
| Model Lab | Собрать синтетический набор | Build synthetic development set | Create synthetic CSV | Writable model_lab | Writes synthetic_dev.csv | model_lab/datasets | None | — | Feature errors | models |
| Model Lab | Обучить | Train | Train development model | Dataset loaded | Writes model card | model_lab models | None | No dataset | Missing values / train error | models |
| Model Lab | Включить выбранную модель в анализ | Enable selected model in analysis | Opt-in ML stage | Selected model + trust | Sets enabled_model_ids | settings | None | No selection / trust declined | Foreign model warning | models |
| Settings | Сохранить / Сброс | Save / Reset | Persist or reload settings | — | Writes settings store | settings file | None | — | IO error | settings |
| Settings | Язык интерфейса | Interface language | Switch EN/RU | — | Retranslates UI | settings | None | — | — | settings |
| Settings | Масштаб интерфейса | Interface scale | UI scale percent | — | Applies scale preference | settings | None | — | — | settings |
| Help | Восстановить введения | Restore introductions | Restore page intros | — | Shows intro panels | settings | None | — | — | help |

Scientific status on Results is always one of: Automatic candidate / Owner-reviewed / Expert-confirmed. Default automatic rows must never be read as confirmed classifications.


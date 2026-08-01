"""One-shot bootstrap for knowledge maps and required docs (IML-0/1)."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "knowledge_base"
DOCS = ROOT / "docs"


def write_source_index() -> None:
    sources = [
        dict(
            source_id="A3L006",
            source_type="journal_article",
            path=r"E:\ionog\conference_presentation\Статьи\Automatic_classification_of_spread-F_types_in_iono.pdf",
            title="Automatic classification of spread-F types in ionogram images using SVM and CNN",
            authors="Benchawattananon et al.",
            year="2024",
            edition="",
            DOI_or_ISBN="10.1186/s40623-024-02002-x",
            language="en",
            printed_pages="1-14",
            pdf_pages="14",
            relevance="high_reference_taxonomy",
            scientific_status="verified_secondary",
            rights_status="cc_by_4_0",
            notes_ru="Таксономия FSF/RSF/MSF; не идентична Article 2",
            notes_en="FSF/RSF/MSF taxonomy; not identical to Article 2",
            sha256="0d598c4c0dce37e1922bfe1cb67db3ad5a2c0c1bdd344ea6ae1d741a07197ef5",
        ),
        dict(
            source_id="A3L007",
            source_type="book_proceedings",
            path=r"E:\ionog\conference_presentation\Статьи\book-2008.pdf",
            title="Труды ИПГ им. Е.К. Фёдорова. Выпуск 87",
            authors="ИПГ/Росгидромет",
            year="2008",
            edition="87",
            DOI_or_ISBN="",
            language="ru",
            printed_pages="14-17 (key)",
            pdf_pages="212",
            relevance="virtual_height_OX",
            scientific_status="verified_primary",
            rights_status="copyright_metadata_only",
            notes_ru="Действующая vs истинная высота; O/X",
            notes_en="Virtual vs true height; O/X",
            sha256="44bba3f248c34a2a626c5bb8352de7ddcf57ff06288c87964ca3456685f633fe",
        ),
        dict(
            source_id="A3L014",
            source_type="book",
            path=r"E:\ionog\conference_presentation\Статьи\Kotonaeva_Blok_1-416.pdf",
            title="Системный мониторинг ионосферы",
            authors="Котонаева Н.Г. (ed.)",
            year="2019",
            edition="",
            DOI_or_ISBN="978-5-9221-1878-1",
            language="ru",
            printed_pages="рис.6 area",
            pdf_pages="416",
            relevance="monitoring_examples",
            scientific_status="applicable_with_limitations",
            rights_status="copyright_all_rights",
            notes_ru="Не специализированный атлас SF",
            notes_en="Not a dedicated SF atlas",
            sha256="576494458600accf325f15db3ac18b29e35858c68d0acd03ff7d426df04dece4",
        ),
        dict(
            source_id="A3L015",
            source_type="technical_note",
            path=r"E:\ionog\conference_presentation\Статьи\nbstechnicalnote145.pdf",
            title="Equatorial Spread F",
            authors="Calvert, Wynne",
            year="1962",
            edition="NBS TN 145",
            DOI_or_ISBN="10.6028/nbs.tn.145",
            language="en",
            printed_pages="1+",
            pdf_pages="120",
            relevance="equatorial_background",
            scientific_status="applicable_with_limitations",
            rights_status="gov_publication",
            notes_ru="Не переносить на Казань (C04)",
            notes_en="Do not transfer to Kazan (C04)",
            sha256="816a2c08d7521cf7c5a8382c2ebe36e1b34e288ddd8611ed77549c0a38aaee52",
        ),
        dict(
            source_id="A3L018",
            source_type="journal_article",
            path=r"E:\ionog\conference_presentation\Статьи\Spread-F-in-the-Midlatitude-Ionosphere-According-to-DPS-4-Ionosonde-Data.pdf",
            title="F-рассеяние в среднеширотной ионосфере по данным DPS-4",
            authors="Панченко В.А. и др.",
            year="2018",
            edition="",
            DOI_or_ISBN="10.1134/S0016793218020160",
            language="ru/en",
            printed_pages="241-249",
            pdf_pages="10",
            relevance="midlatitude_SF_definition",
            scientific_status="verified_primary",
            rights_status="journal_copyright",
            notes_ru="Операциональное определение SF",
            notes_en="Operational SF definition",
            sha256="c4d9efa51b39df6326f3dc428f69616da94de177318d96e3b68f0df3400c6dd1",
        ),
        dict(
            source_id="A2_PROTOCOL",
            source_type="project_protocol",
            path=r"E:\ionog\conference_presentation\02_article_2_morphology_temporal_dynamics\docs\ARTICLE2_MORPHOLOGY_RULE_CANDIDATE_RU.md",
            title="Article 2 morphology rule candidate",
            authors="project",
            year="2026",
            edition="",
            DOI_or_ISBN="",
            language="ru",
            printed_pages="n/a",
            pdf_pages="n/a",
            relevance="canonical_labels",
            scientific_status="development_only",
            rights_status="project_internal",
            notes_ru="Канонические метки frequency/range/mixed/none/indeterminate",
            notes_en="Canonical frame labels",
            sha256="",
        ),
        dict(
            source_id="CALSTAT",
            source_type="project_calibration",
            path=r"E:\ionog\conference_presentation\spread_f_article\docs\CALIBRATION_STATUS.md",
            title="Calibration status Amp_all archive",
            authors="project",
            year="2026",
            edition="",
            DOI_or_ISBN="",
            language="ru",
            printed_pages="n/a",
            pdf_pages="n/a",
            relevance="instrument_profile",
            scientific_status="verified_secondary",
            rights_status="project_internal",
            notes_ru="Amp_all shape, ff, minute mapping, Gate2 open",
            notes_en="Amp_all shape, ff, minute mapping, Gate2 open",
            sha256="",
        ),
        dict(
            source_id="GETION",
            source_type="legacy_matlab",
            path=r"E:\ionog\conference_presentation\mscripts\get_ionogram.m",
            title="get_ionogram.m legacy renderer",
            authors="legacy",
            year="",
            edition="",
            DOI_or_ISBN="",
            language="matlab",
            printed_pages="n/a",
            pdf_pages="n/a",
            relevance="frame_slice_height_scale",
            scientific_status="development_only",
            rights_status="project_internal",
            notes_ru="i*256 slice; *2.5 height; DateVector minute-1 quirk",
            notes_en="Legacy slice and height scale",
            sha256="",
        ),
        dict(
            source_id="FREG",
            source_type="formula_register",
            path=r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\18_radiophysics_framework\ARTICLE3_VERIFIED_FORMULA_REGISTER.csv",
            title="Article3 verified formula register",
            authors="project L0",
            year="2026",
            edition="",
            DOI_or_ISBN="",
            language="ru/en",
            printed_pages="n/a",
            pdf_pages="n/a",
            relevance="formula_policy",
            scientific_status="verified_primary",
            rights_status="project_internal",
            notes_ru="Источник статусов формул для IML",
            notes_en="Formula status source for IML",
            sha256="",
        ),
        dict(
            source_id="CLM",
            source_type="claim_matrix",
            path=r"E:\ionog\conference_presentation\04_article_3_dawn_dusk_solar_terminator\18_radiophysics_framework\ARTICLE3_PHYSICS_CLAIM_SOURCE_MATRIX.csv",
            title="Article3 physics claim source matrix",
            authors="project L0",
            year="2026",
            edition="",
            DOI_or_ISBN="",
            language="ru",
            printed_pages="n/a",
            pdf_pages="n/a",
            relevance="claim_policy",
            scientific_status="verified_primary",
            rights_status="project_internal",
            notes_ru="C01-C04",
            notes_en="C01-C04",
            sha256="",
        ),
        dict(
            source_id="A3L004",
            source_type="incomplete_download",
            path=r"E:\ionog\conference_presentation\Статьи\97-106.pdf.crdownload",
            title="incomplete",
            authors="",
            year="",
            edition="",
            DOI_or_ISBN="",
            language="",
            printed_pages="",
            pdf_pages="",
            relevance="none",
            scientific_status="unreadable",
            rights_status="unknown",
            notes_ru="Незавершённая загрузка",
            notes_en="Incomplete download",
            sha256="5b2047cc4b8bbfab66886cffed88fbe2eaf47ced8748c6d1696ac79b242a73eb",
        ),
    ]
    fields = list(sources[0].keys())
    with open(KB / "PROJECT_SCIENTIFIC_SOURCE_INDEX.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sources)


def write_knowledge_maps() -> None:
    (KB / "PROJECT_KNOWLEDGE_MAP_EN.md").write_text(
        """# Project Knowledge Map (EN) — Ionogram Morphology Lab

## What is known

1. Canonical morphology labels (Article 2): frequency, range, mixed, none, indeterminate (+ artifact / not_assessable).
2. KFU Cyclone Amp_all structure: `(368640, 400)` = 1440×256×400; slice `(i-1)*256:i*256`; ff ≈ 1.5–9.081 step 0.019; nominal ×2.5 km; minute = index−1.
3. Station coordinates 55.834705°N, 48.830660°E are author-attested, not MAT-embedded.
4. Claim policy C01–C04 and formula statuses F001–F007 (from allowed radiophysics framework files).
5. Reference taxonomy candidates: Panchenko 2018, Benchawattananon 2024, ИПГ 2008; equatorial Calvert is non-transferable background.

## What is uncertain

Absolute Amp_all MHz/km calibration; amplitude units; hour-boundary clock mapping; O/X polarimetry in Amp_all; exact Bench↔Article2 class equivalence; institutional image redistribution clearance.

## What must not be claimed

Confirmed physical mechanism; proved solar cause; confirmed Rayleigh–Taylor from morphology alone; true height = index×2.5; proven O/X from Amp_all; validated accuracy before validation; URSI MHz/km thresholds as Amp_all metrology.

## Isolation

Article 3 secret, blinded renders, review progress, and blinded review app paths are blocked and unused.

## Separate levels

Visible morphology (candidate) ≠ physical interpretation ≠ causal mechanism.
""",
        encoding="utf-8",
    )
    (KB / "PROJECT_KNOWLEDGE_MAP_RU.md").write_text(
        """# Карта знаний проекта (RU) — Лаборатория морфологии ионограмм

## Что известно

1. Канонические метки Article 2: frequency, range, mixed, none, indeterminate (+ artifact / not_assessable).
2. Структура Amp_all «Циклон» КФУ: `(368640, 400)`; срез кадра; ff ≈ 1.5–9.081; номиналь ×2.5 км; минута = индекс−1.
3. Координаты 55.834705°N, 48.830660°E — авторски засвидетельствованы.
4. Политика C01–C04 и статусы формул F001–F007.
5. Эталонная таксономия: Панченко 2018, Benchawattananon 2024, ИПГ 2008; экваториальный Calvert не переносится.

## Что неясно

Калибровка МГц/км; единицы амплитуды; границы часа; O/X в Amp_all; эквивалентность таксономий; clearance изображений.

## Что нельзя утверждать

Подтверждённый механизм; доказанная солнечная причина; RT из морфологии; истинная высота = индекс×2.5; доказанное O/X; «валидированная точность» до валидации.

## Изоляция

Секретные и слепые материалы Article 3 заблокированы.

## Три уровня

Видимая морфология ≠ физическая интерпретация ≠ причинный механизм.
""",
        encoding="utf-8",
    )


DOCS_CONTENT: dict[str, str] = {}


def _d(name: str, body: str) -> None:
    DOCS_CONTENT[name] = body.strip() + "\n"


def define_docs() -> None:
    _d(
        "USER_GUIDE_EN.md",
        """# User Guide (EN) — Ionogram Morphology Lab

1. Launch via `scripts/run_dev.ps1` or `IonogramMorphologyLab.exe`.
2. Choose English or Russian.
3. Create a New Project (default workspace under `workspaces/`).
4. Import a MAT file or folder (external / synthetic / approved non-blinded only).
5. Review Data Audit; configure Instrument Profile (KFU provisional or wizard).
6. View raw ionograms; run Batch Analysis; inspect Results.
7. Export RU/EN reports. Original MAT files are never modified.

Results are **candidate morphology** and require expert review.
""",
    )
    _d(
        "USER_GUIDE_RU.md",
        """# Руководство пользователя (RU) — Лаборатория морфологии ионограмм

1. Запуск: `scripts/run_dev.ps1` или `IonogramMorphologyLab.exe`.
2. Выберите язык.
3. Создайте проект (`workspaces/` по умолчанию).
4. Импортируйте MAT (внешние / синтетические / одобренные неслепые данные).
5. Аудит → профиль инструмента → просмотр → пакетный анализ → результаты.
6. Экспорт отчётов RU/EN. Исходные MAT не изменяются.

Результаты — **кандидатная морфология**, требуется экспертная проверка.
""",
    )
    _d(
        "SCIENTIFIC_METHOD_EN.md",
        """# Scientific Method (EN)

Pipeline: import → profile → quality audit → raw render → segmentation → interpretable features → source-traceable rules → reference comparison → disagreement/abstention → expert decision (separate) → reproducible exports.

Morphology, physical interpretation, and causal mechanism remain separate. Solar/dawn/dusk context is disabled for morphology in IML-1.
""",
    )
    _d(
        "SCIENTIFIC_METHOD_RU.md",
        """# Научный метод (RU)

Конвейер: импорт → профиль → аудит качества → сырой рендер → сегментация → признаки → правила с прослеживаемостью → сравнение с эталонами → разногласия/воздержание → решение эксперта (отдельно) → воспроизводимый экспорт.

Морфология, интерпретация и механизм разделены. Солнечный/dawn-dusk контекст отключён для морфологии в IML-1.
""",
    )
    _d(
        "INSTRUMENT_PROFILE_GUIDE_EN.md",
        """# Instrument Profile Guide (EN)

Use built-in `kfu_cyclone_2013_2014` (status: **provisional**) or the Profile Wizard.
User-defined profiles are always `user-defined-unverified` and must never be shown as instrument-verified.
Warnings: nominal virtual height; not true height; provisional archive time; profile-specific structure.
""",
    )
    _d(
        "INSTRUMENT_PROFILE_GUIDE_RU.md",
        """# Руководство по профилю инструмента (RU)

Встроенный `kfu_cyclone_2013_2014` (**provisional**) или мастер профиля.
Пользовательские профили всегда `user-defined-unverified`.
Предупреждения: номинальная виртуальная высота; не истинная высота; предварительное время архива.
""",
    )
    _d(
        "REFERENCE_ATLAS_POLICY_EN.md",
        """# Reference Atlas Policy (EN)

Default install ships **metadata citations only**. Copyrighted figures are not redistributed.
Optional local packs may add legally accessible images with documented rights.
Wording: “The visible morphology is structurally similar to…” — never “the same physical event.”
""",
    )
    _d(
        "REFERENCE_ATLAS_POLICY_RU.md",
        """# Политика атласа эталонов (RU)

В установку входят **только метаданные и цитаты**. Чужие рисунки не распространяются.
Локальные пакеты — только при документированных правах.
Формулировка: «Видимая морфология структурно похожа на…».
""",
    )
    _d(
        "VALIDATION_PLAN_EN.md",
        """# Validation Plan (EN)

1. Synthetic unit/integration tests (not scientific validation).
2. Optional Article 2 development smoke tests only if permissions allow.
3. Future: independent expert review; frozen labels; date-based splits; abstention metrics.
4. Article 3 labels remain inaccessible until blinded review completion + explicit approval.
5. Do not claim validated accuracy in manuscripts before independent validation.
""",
    )
    _d(
        "VALIDATION_PLAN_RU.md",
        """# План валидации (RU)

1. Синтетические тесты (не научная валидация).
2. Опциональные smoke-тесты Article 2 только при разрешении.
3. Далее: независимая экспертная проверка; заморозка меток; сплиты по датам.
4. Метки Article 3 недоступны до завершения слепого разбора и явного разрешения.
5. Не заявлять валидированную точность до независимой валидации.
""",
    )
    _d(
        "DEVELOPER_GUIDE.md",
        """# Developer Guide

```powershell
cd IonogramMorphologyLab
python -m pip install -e .[dev]
./scripts/run_dev.ps1
./scripts/run_tests.ps1
```

Package: `src/ionogram_morphology_lab`. Entry: `ionogram_morphology_lab.app.main:main`.
Do not access Article 3 forbidden paths. Do not train on Article 3 labels.
""",
    )
    _d(
        "DATA_AND_MODEL_LIMITATIONS_EN.md",
        """# Data and Model Limitations (EN)

- No absolute calibration; nominal virtual height.
- No polarimetry guarantee → O/X abstention.
- Rule thresholds may be development_calibration — not literature constants.
- No final ML model in IML-1.
- Synthetic data ≠ scientific validation.
""",
    )
    _d(
        "DATA_AND_MODEL_LIMITATIONS_RU.md",
        """# Ограничения данных и моделей (RU)

- Нет абсолютной калибровки; номинальная виртуальная высота.
- Нет гарантии поляриметрии → воздержание по O/X.
- Пороги правил могут быть development_calibration.
- Финальная ML-модель в IML-1 не обучалась.
- Синтетика ≠ научная валидация.
""",
    )
    _d(
        "ARTICLE_METHODS_WORDING_EN.md",
        """# Article Methods Wording (EN)

Allowed: “A software-assisted ionogram morphology analysis system was developed, combining reproducible rendering, interpretable feature measurement, source-traceable reference and rule comparison, and abstention under ambiguity.”

Do not write: “the program accurately identifies all Spread-F events”; “the algorithm proves the physical mechanism”; “the system is validated” before validation exists.
""",
    )
    _d(
        "ARTICLE_METHODS_WORDING_RU.md",
        """# Формулировки для раздела методов (RU)

Допустимо: «Разработано программное средство поддержки морфологического анализа ионограмм, объединяющее воспроизводимое построение изображений, измерение интерпретируемых признаков, сопоставление со ссылочно-прослеживаемыми примерами и правилами, а также механизм воздержания при неоднозначности.»

Не писать: «программа точно выявляет все события Spread-F»; «алгоритм доказывает механизм»; «система валидирована» до валидации.
""",
    )


def write_iml_reports() -> None:
    reports = {
        "IML0_EXISTING_PROJECT_AND_LITERATURE_AUDIT_EN.md": """# IML-0 Existing Project and Literature Audit (EN)

Audited (read-only, allowed paths): `Статьи\\`, `17_literature_audit`, `18_radiophysics_framework`, `19_cross_project_recommendations`, Article 1/2, dissertation maps, `00_workspace_audit`, `spread_f_article` calibration docs, `mscripts/get_ionogram.m`.

Key outcomes: formula/claim registers copied into IML knowledge_base with disabled candidate_not_ready formulas; KFU profile drafted as provisional; morphology terminology mapped with cautions; Article 3 blinded materials not accessed.
""",
        "IML0_EXISTING_PROJECT_AND_LITERATURE_AUDIT_RU.md": """# IML-0 Аудит существующего проекта и литературы (RU)

Прочитаны разрешённые источники (см. EN). Слепые материалы Article 3 не открывались. Регистры формул/утверждений перенесены в knowledge_base; профиль КФУ — provisional.
""",
        "IML0_SCIENTIFIC_GAPS_AND_BLOCKERS_EN.md": """# IML-0 Scientific Gaps and Blockers (EN)

1. Absolute Amp_all calibration open (Gate2).
2. Copyrighted reference figures not packable by default.
3. O/X not separable in Amp_all.
4. Article 3 labels unavailable (by design).
5. Development-calibrated rule thresholds ≠ literature constants.
6. Institutional image redistribution clearance incomplete.
""",
        "IML0_SCIENTIFIC_GAPS_AND_BLOCKERS_RU.md": """# IML-0 Научные пробелы и блокеры (RU)

1. Абсолютная калибровка Amp_all открыта.
2. Чужие рисунки нельзя класть в установщик по умолчанию.
3. O/X в Amp_all не разделяется.
4. Метки Article 3 недоступны (намеренно).
5. Пороги development_calibration ≠ константы литературы.
6. Clearance изображений неполный.
""",
        "IML1_MVP_ARCHITECTURE.md": """# IML-1 MVP Architecture

Desktop: PySide6. Package: `ionogram_morphology_lab` under `src/`.
Layers: security/blocklist → importers/cache → instrument_profiles → rendering → segmentation/features → similarity → rules/disagreement/reference_atlas → projects/database → reports → UI.
Workspaces hold runs; SQLite stores metadata only; MAT sources remain untouched.
Future ML via `classifiers.interfaces`; context via `plugins.context` (disabled for morphology).
""",
        "IML1_MAT_IMPORT_SUPPORT_MATRIX.md": """# MAT Import Support Matrix

| Format | Adapter | Status |
|---|---|---|
| MATLAB v5/v7 | scipy_mat_v5 | supported |
| MATLAB v7.3 HDF5 | hdf5_mat_v73 | supported |
| Known KFU Amp_all | known_kfu_cyclone | supported when shape matches |
| Generic user profile | generic_user_profile | supported via wizard |
| MATLAB Engine | optional_matlab_engine | optional |
| CRC / Win32 error 23 | — | report `CRC_error` / `unreadable_disk_crc_error`; continue batch |
""",
        "IML1_FEATURE_REGISTRY_EN.md": """# Feature Registry (EN)

See `src/ionogram_morphology_lab/features/registry.py` for the full list (30+ features).
Groups: trace visibility; frequency-spread-compatible; range-spread-compatible; mixed; O/X ambiguity; interference; temporal.
No sunrise/sunset/solar variables.
""",
        "IML1_FEATURE_REGISTRY_RU.md": """# Реестр признаков (RU)

Полный список — в `features/registry.py`. Солнечные/dawn-dusk признаки отсутствуют.
""",
        "IML1_RULE_PROVENANCE_REPORT_EN.md": """# Rule Provenance Report (EN)

Active rules R001–R006 with source/claim links. R099 unsupported disabled.
Threshold origins include development_calibration and derived_from_verified_definition — not silently presented as literature constants.
candidate_not_ready formulas (F005/F006) excluded from rule physics.
""",
        "IML1_RULE_PROVENANCE_REPORT_RU.md": """# Отчёт о прослеживаемости правил (RU)

Активны R001–R006; R099 отключён. F005/F006 не используются. Пороги development_calibration явно помечены.
""",
        "IML1_REFERENCE_ATLAS_REPORT_EN.md": """# Reference Atlas Report (EN)

9 metadata reference cases (REF001–REF009). Rights-restricted images unavailable in default install. Equatorial case flagged C04.
""",
        "IML1_REFERENCE_ATLAS_REPORT_RU.md": """# Отчёт по атласу эталонов (RU)

9 метаданных эталонов. Рисунки с ограничениями прав не включены. Экваториальный кейс с предупреждением C04.
""",
        "IML1_SECURITY_AND_ARTICLE3_ISOLATION_AUDIT.md": """# Security and Article 3 Isolation Audit

Blocklist fragments cover secret/, 11_rendered_frames/, 12_rendered_contact_sheets/, 21_review_progress/, 20_blinded_review_app/.
Telemetry disabled; no network requests by design.
Source MAT never overwritten. Workspaces separated.
""",
        "IML1_VISUAL_QA_EN.md": """# Visual QA (EN)

Raw view uses nearest-neighbor, no default smoothing/interpolation. Derived views labeled. Nominal virtual height axis wording enforced. Synthetic demos labeled SYNTHETIC.
""",
        "IML1_VISUAL_QA_RU.md": """# Визуальный QA (RU)

Сырой вид: nearest, без сглаживания. Производные виды помечены. Подпись номинальной виртуальной высоты. Синтетика помечена.
""",
    }
    for name, body in reports.items():
        (DOCS / name).write_text(body.strip() + "\n", encoding="utf-8")


def main() -> None:
    KB.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    write_source_index()
    write_knowledge_maps()
    define_docs()
    for name, body in DOCS_CONTENT.items():
        (DOCS / name).write_text(body, encoding="utf-8")
    write_iml_reports()
    print("KB + docs written")


if __name__ == "__main__":
    main()

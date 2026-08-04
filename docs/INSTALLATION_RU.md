# Установка — Ionogram Morphology Lab 1.1.1

Руководство по portable-релизу и установке из исходников. MATLAB и Octave **не обязательны**; импорт, просмотр, анализ, экспертная проверка и отчёты работают без них.

## Системные требования

| Компонент | Минимум | Примечание |
|-----------|---------|------------|
| ОС (основная) | Windows 10/11 x64 | Portable `.exe` и GUI на PySide6 |
| ОС (разработка) | Windows, Linux, macOS | Python 3.10+ из исходников |
| ОЗУ | 8 ГБ рекомендуется | Больше для крупных пакетов MAT и кэша |
| Диск | Свободное место под workspace | Кэш Zarr и экспорты растут с проектами |
| MATLAB / Octave | Опционально | Только для запуска скриптов в MATLAB Studio |
| Сеть | Не требуется | Локальное приложение |

## Portable-пакет

1. Распакуйте каталог релиза в место с правами на чтение и запуск.
2. Сохраняйте файлы вместе — не отделяйте `_internal/` от исполняемого файла.
3. Укажите **доступную для записи папку workspace** вне каталога установки.
4. Запустите `IonogramMorphologyLab.exe`.
5. При первом запуске выберите **English** или **Русский**; смена языка: **Settings → General → Interface language**.

Portable-сборка включает документацию, пакеты правил, учебные синтетические данные и ресурсы MATLAB Studio. Среда MATLAB **не** устанавливается автоматически.

## Установка для разработки

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m ionogram_morphology_lab.app.main
```

Проверка перед вкладом в код:

```bash
python -m pytest
python scripts/validate_version_consistency.py
python scripts/check_repository_hygiene.py
python scripts/validate_readme.py
python scripts/validate_docs.py
```

Скрипты в `packaging/` — для сопровождения релиза; артефакты в `dist/` не хранятся в исходном репозитории.

## Первый запуск

1. Выберите язык интерфейса.
2. На **Home** создайте **New Project** в writable workspace.
3. Импортируйте учебный файл из [`synthetic_data/`](../synthetic_data/) до исследовательских MAT.
4. Откройте **Data Audit** и проверьте форму массива и предупреждения.
5. Заполните или выберите **Instrument Profile** с честным статусом верификации.
6. В **Viewer** выполните **Build cache** для производного Zarr при необходимости.
7. Запустите небольшой **Batch Analysis** и просмотрите **Results** как кандидатные предложения.

## Опциональные backend MATLAB Studio

**Settings → MATLAB**:

| Backend | Когда использовать |
|---------|-------------------|
| `none` | Библиотека и манифесты; выполнение отключено |
| `matlab_engine` | Локальный лицензированный MATLAB с Engine API |
| `external_matlab` | Внешний вызов `matlab -batch` |
| `octave` | GNU Octave в PATH |

Состояние `none` на машине без MATLAB — нормально. Основные сценарии работают без выполнения скриптов.

## Удаление и сохранение данных

Удаляя portable-каталог, заранее архивируйте проекты, экспорты и записи происхождения (provenance) из workspace. Исходные MAT в обычном режиме не изменяются; удаление установки не затрагивает workspace, если проекты хранились отдельно.

## Проблемы при установке

| Симптом | Действие |
|---------|----------|
| Приложение не запускается | Проверьте целостность bundled-зависимостей; попробуйте запуск из исходников |
| Не создаётся проект | Укажите writable-папку вне Program Files |
| Сбой импорта | [TROUBLESHOOTING_RU.md](TROUBLESHOOTING_RU.md), [DATA_FORMATS.md](DATA_FORMATS.md) |
| Backend MATLAB недоступен | Встроенные методы; [MATLAB_STUDIO_GUIDE_RU.md](MATLAB_STUDIO_GUIDE_RU.md) |

## Связанные документы

- [Руководство пользователя](USER_GUIDE_RU.md)
- [Научное руководство](SCIENTIFIC_GUIDE_RU.md)
- [FAQ_RU.md](FAQ_RU.md)
- [SECURITY.md](../SECURITY.md)

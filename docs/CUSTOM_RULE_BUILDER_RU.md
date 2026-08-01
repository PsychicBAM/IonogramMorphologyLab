# Custom Rule Builder — мастер без кода

**Версия:** 1.1.1  
**Аудитория:** аналитики и разработчики методов, которым нужны **версионированные правила со ссылкой на источник** без написания Python.

**Rule Builder** создаёт локальные определения `ScientificRule` в YAML в проекте или пользовательской библиотеке. Сохранённое правило — **кандидатная процедура по evidence**, а не валидированная наука до тестирования по вашему протоколу.

> **Честная область применения:** мастер формирует предикаты и **предпросмотр** кода. Прохождение мастера или генерация MATLAB/Python **не** означает peer review, operational approval или универсальную точность.

## Когда использовать Rule Builder

| Используйте Rule Builder, если… | Иначе… |
|----------------------------------|--------|
| Есть документированное условие из литературы | Нужен black-box ML → **Model Lab** (только разработка) |
| Нужны bilingual metadata и provenance | Разовая ручная разметка → **Expert Review** |
| Будете тестировать на размеченной dev-выборке | Нет меток → сначала экспертная разметка |
| Нужно отключить устаревшие правила без удаления истории | Удаление audit trail не поддерживается |

## Понятия

| Термин | Значение |
|--------|----------|
| **Rule ID** | Стабильный идентификатор — не переиспользуйте для другой логики |
| **Target axis** | layer, morphology, ambiguity, quality, interference, parameter — **одна ось на правило** |
| **Condition** | feature + operator + threshold + units |
| **Abstention / exclusion** | Явный путь при недостатке evidence |
| **Status** | draft, project_approved, source_verified — strict pipeline фильтрует |
| **Version** | Каждое сохранение — новый snapshot |

## Workflow мастера

### 1. Открыть Rule Builder

**Home** (режим Expert) или меню → **Rule Builder** → **New rule**.

![Rule Builder](../assets/screenshots/rule_builder_ru.png)

*Alt: мастер Rule Builder с предпросмотром условий.*

### 2. Идентификация и цель

- **Rule ID** — snake_case;
- **Names** EN/RU;
- **Target axis** — одна первичная научная ось;
- **Proposed result** — токен при срабатывании (не claim о физическом механизме).

### 3. Условия

| Элемент | Рекомендация |
|---------|--------------|
| **Feature** | Из registry для вашего профиля |
| **Operator** | gte, lte, eq, between, … |
| **Threshold** | Число с **единицами** |
| **Logic** | AND между условиями (если Advanced не задаёт иное) |

Задайте **abstention** (нет features / низкое quality) и **exclusions** (профили, помехи).

### 4. Применимость и provenance

- Профили приборов / домены;
- Альтернативы из литературы;
- Допущения и ограничения;
- Source IDs и страницы;
- **Verification status** — начинайте с `draft`.

Статусы `source_verified` / `project_approved` — только с **записями ревью**, не по факту сохранения в мастере.

### 5. Предпросмотр кода

**Preview generated code** — Python/MATLAB в Advanced.

Код для **инспекции**, не научное одобрение приложения.

### 6. Сохранение

**Save rule** — версионированный YAML. При конфликте ID смотрите history.

### 7. Rule Testing Lab

1. Размеченная dev-выборка.
2. Threshold sweep, confusion vs labels.
3. Разбор FP на ambiguous и negative.
4. Split по дате — без утечки соседних кадров.

[Rule testing guide (RU)](RULE_TESTING_GUIDE_RU.md).

### 8. Экспорт / импорт pack

- **Export pack** — ZIP с `pack.yaml`, `rules/*.yaml`.
- **Import pack** — только доверенные источники; v1.1.1 отклоняет unsafe paths и oversize.

Отключайте устаревшие правила, не удаляя provenance.

## UX-режимы

| Режим | Rule Builder |
|-------|--------------|
| Guided | Скрыт или отложен |
| Research | Виден, акцент на мастере |
| Expert | Полные вкладки + Advanced |

## Чеклист качества

Перед `project_approved`:

- [ ] Единицы у всех порогов
- [ ] Ограничения профиля/домена
- [ ] Exclusions для помех
- [ ] Bibliographic source
- [ ] Negative и ambiguous в Rule Testing Lab
- [ ] Текст limitations
- [ ] Abstention протестирован
- [ ] EN/RU names проверены при bilingual отчётах

Bundled synthetic examples — только **поведение реализации**.

## Strict vs permissive

| Фильтр | Поведение |
|--------|-----------|
| Permissive | Draft с предупреждениями |
| Scientific strict | Только approved/verified |

Strict — после записей тестирования.

## Безопасность

- Импорт pack — [Threat model](THREAT_MODEL.md).
- YAML через `yaml.safe_load`.
- Сгенерированный код — как любой скрипт до внешнего запуска.

## Связанные документы

- [RULE_TESTING_GUIDE_RU.md](RULE_TESTING_GUIDE_RU.md)
- [MORPHOLOGY_METHODS_RU.md](MORPHOLOGY_METHODS_RU.md)
- [SCIENTIFIC_LIMITATIONS_RU.md](SCIENTIFIC_LIMITATIONS_RU.md)
- [QUICK_START_RU.md](QUICK_START_RU.md)

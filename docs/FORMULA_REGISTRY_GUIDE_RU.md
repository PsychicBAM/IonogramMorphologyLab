# Руководство по реестру формул (RU) — Phase 4A / 4A.1

Файл реестра: `knowledge_base/FORMULA_REGISTRY.yaml`

## Классификация

1. `exact_physical_formula` — точная физическая формула  
2. `exact_signal_processing_formula` — точная формула обработки сигнала  
3. `observational_definition` — наблюдательное определение  
4. `morphology_definition` — морфологическое определение  
5. `instrument_specific_procedure` — процедура, зависящая от прибора  
6. `project_engineering_heuristic` — проектная эвристика  
7. `unsupported_or_incomplete` — не поддержано / неполно  

Проектные эвристики нельзя показывать в интерфейсе и отчётах как уравнения, взятые напрямую из литературы.

## Сводка (вычисляется)

Группы `summary` формируются из `classification` (не копируются вручную):  
`exact_physical_formulas`, `observational_definitions`, `exact_signal_processing_formulas`, `instrument_specific_procedures`, `morphology_definitions`, `project_engineering_heuristics`, `unsupported_or_disabled`.  
`observational_definition` (F002) не входит в `exact_physical_formulas`.  
Инструментальные пересчёты осей не относятся к точным физическим формулам.

## Точная локализация источника (4A.1)

Для source-supported записей обязательны `source_location` и `expression_kind`.  
Расплывчатые формулировки вроде «operational morphology classes» отклоняются валидатором.

## Пояснения

Страница **Исходные числовые данные → Пояснения формул**: что вычисляется, из каких данных, формула, переменные, единицы, источник и страница, применимость, неприменимость, статус проверки.

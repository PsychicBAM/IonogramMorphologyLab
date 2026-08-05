# Phase 4C.2 … 4C.2b.3 — Owner QA Checklist

Pilot expert-review corpus — **not** a scientific validation set.  
Пилотный корпус экспертной разметки — **не** является научно валидированным контрольным набором.

**Expected Build Identity:** `4C.2b.3`  
**Expected EXE SHA-256:** `8758777CBCEFFCC3BE41DBCF38D8A21D5CB24829968B82983274A34BB8B5DFCB`  
**Prior visual build:** `4C.2b.2` / `DDF881E809D9D51D4A506FB758B47BEEF6BACB5ECDF6DC2BF5A8FF99D983E346`

## 4C.2b.3 — Comparison idempotency / current-state / semantics (owner visual required)

| # | Step (EN) | Шаг (RU) | Pass? |
|---|-----------|----------|-------|
| D1 | Five-item corpus: comparisons never exceed 5/5 after double-save | Пять кадров: сравнения не выше 5/5 после повторного сохранения | ☐ |
| D2 | Summary comparisons + candidate distribution totals ≤ 5 | Сводка: сравнения и распределение кандидата ≤ 5 | ☐ |
| D3 | Revisit saved comparison → read-only «Сравнение сохранено» | Повторный заход: только чтение, «Сравнение сохранено» | ☐ |
| D4 | Corrected comparison revision with reason; progress still 5/5 | Исправленная версия сравнения; прогресс 5/5 | ☐ |
| D5 | Before reveal: pending, not “Expert abstained” | До показа: «Кандидат ещё не показан…», не «воздержался» | ☐ |
| D6 | After reveal indeterminate → human abstained with explanation | После показа «Неопределённо» → объяснение воздержания | ☐ |
| D7 | Guided/Summary: second reviewer optional | Второй эксперт не обязателен | ☐ |
| D8 | Optional second review does not change comparison 5/5 | Вторая оценка не меняет прогресс сравнений | ☐ |
| D9 | Queue: explicit columns/statuses; no generic Yes for comparison | Очередь: явные статусы; без «Да» для сравнения | ☐ |
| D10 | ⋯ → Validate and repair derived state on affected corpus | ⋯ → Проверить и восстановить производное состояние | ☐ |
| D11 | Technical details collapsed by default | Технические сведения свёрнуты | ☐ |
| D12 | Guided card wider / structured sections | Guided шире, структурированные блоки | ☐ |
| D13 | RU/EN switch; no Not Responding | RU/EN; нет «Не отвечает» | ☐ |

## Previously owner-accepted (behaviour / visual)

| Phase | Notes |
|-------|-------|
| 4C.2b | Scientific/workflow contracts |
| 4C.2b.1 | Guided card, Rapid splitter, comment groups, toolbar |
| 4C.2b.2 | Comparison handoff, locked Review, corrected review revision |

## Result template

```
Date:
EXE SHA-256:
Build Identity: 4C.2b.3 (expected)

Comparison progress integrity: PASS / FAIL
Idempotent save / read-only revisit: PASS / FAIL
Abstention semantics: PASS / FAIL
Optional second reviewer clarity: PASS / FAIL
Queue status clarity: PASS / FAIL
Guided density / Technical collapse: PASS / FAIL
Derived-state repair (if needed): PASS / FAIL / N/A
RU localization: PASS / FAIL

Notes:
```

## Reminders

- Repair does not delete history; it reconstructs current-state projection.
- Direct unfreeze is not offered — use editable cohort revision or corrected review/comparison revision.
- Strict blinding remains the default for new corpora; older per-item policies are preserved.
- Do not claim accuracy / F1 / ground truth.
- Automated smoke ≠ owner visual PASS.
- No commit / push until accepted.

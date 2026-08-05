# Phase 4C.3 … 4C.3a.2 — Owner QA Checklist

Pilot expert-review campaign — **not** a scientific validation study.  
Пилотная кампания экспертной оценки — **не** является научной валидацией.

**Expected Build Identity:** `4C.3a.2`  
**Owner-verified EXE SHA-256 (visual QA):** `5A3BBC920AB2684CC6B79CB4D02F2132D9DF0B9AD5A66D7255EC988A5A8A081A`  
**Final release-gate rebuild SHA-256:** `1B4C861A43B1E0A14AE4CF5436393F87B70091F284EEB9E981531E5749F6DC60`  
**Prior build (4C.3a.1):** `A5CA0222A03406F15FBF75BBF77422AD5D988763540ADC5FCAD0F39D1ED9C061`

**Note:** Owner visual QA **PASS**. Full pytest release gate completed — see `docs/PHASE4C_FINAL_RELEASE_GATE_REPORT.md`. Clean rebuild SHA may differ from the owner-verified SHA.

## 4C.3a.2 — Batch reveal / auto-compare (owner visual required)

| # | Step (EN) | Шаг (RU) | Pass? |
|---|-----------|----------|-------|
| H1 | Complete all first-round blind reviews | Завершить первый круг слепой оценки | ☐ |
| H2 | Candidate stays hidden until batch action | Кандидат скрыт до пакетного действия | ☐ |
| H3 | Primary CTA: Reveal Candidates and Calculate Comparisons | «Показать кандидатов и рассчитать сравнения» | ☐ |
| H4 | Confirmation text correct; Cancel works | Подтверждение корректно; Отмена работает | ☐ |
| H5 | Batch produces one current comparison per eligible item | По одному текущему сравнению на кадр | ☐ |
| H6 | Summary opens automatically | Сводка открывается | ☐ |
| H7 | Repeat batch → counts unchanged (e.g. 5/5) | Повтор пакета не увеличивает счётчики | ☐ |
| H8 | Per-item mode: Reveal derives comparison; no auto-next | Покадрово: сравнение сразу; без авто-следующего | ☐ |
| H9 | Optional post-comparison note does not change status/count | Необязательный комментарий не меняет статус/счёт | ☐ |
| H10 | Unavailable candidate reported separately | Недоступный кандидат учтён отдельно | ☐ |
| H11 | Campaign Resume routes to batch CTA | «Продолжить работу» → пакетное действие | ☐ |
| H12 | RU/EN; no Not Responding | RU/EN; нет «Не отвечает» | ☐ |

## Prior 4C.3a.1 (accepted)

Owner visual QA for wizard inventory / contrast / hydration: **passed**.

## Result template

```
Date:
EXE SHA-256:
Build Identity: 4C.3a.2 (expected)

Batch reveal CTA: PASS / FAIL
Confirmation: PASS / FAIL
Comparisons = eligible items: PASS / FAIL
Idempotent re-run: PASS / FAIL
Optional note isolated: PASS / FAIL
Summary auto-open: PASS / FAIL

Notes:
```

## Reminders

- Do not claim accuracy / F1 / ground truth.
- Full pytest must run once before commit/push.
- No commit / push until accepted.
- Automated smoke ≠ owner visual PASS.

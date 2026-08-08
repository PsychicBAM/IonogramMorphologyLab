# ML-C.1 / ML-C.1b Owner QA Checklist

**Build Identity:** ML-C.1b  
**Prior ML-C.1 EXE SHA-256:** `2CE8C295A79DC601A8F743A53DC879D23641D97F8B4CB2DA4001F516A561DA7D`  
**ML-C.1a EXE SHA-256:** `84D3F76200A3BBE7E329CF169DFDE6B1D38EE784133957B51471E71A72BE6530`  
**ML-C.1b EXE SHA-256:** `1BA1E89E7B51C32992D7C3D00B807D4854EE2135DF5F25729CBA6322BDC3C484`

## Owner findings from ML-C.1a Development Evaluation (addressed in ML-C.1b)

1. Majority Class predicted / displayed class `m` (truncation of `mixed_spread`) — fixed in baseline `predict` (`np.full(..., dtype=str)` → full string array).
2. Macro F1 / per-class cells showed raw `None` — normal UI now shows `N/A` / `Не определено`; artifacts may still store `null`.
3. Error Analysis blank reference/prediction/context — UI now maps `predictions_development.jsonl` fields; missing values show `—`.
4. Historical malformed completed experiments are **not** rewritten; Verify Integrity reports invalid morphology labels; create **new** experiments after the fix.

## Owner findings from ML-C.1 packaged QA (addressed in ML-C.1a)

1. Completed experiment did not expose a clear Validate/Run path — fixed with primary action bar + immutable completed messaging + New Experiment auto-select.
2. Mixed EN/RU localization — fixed with full page i18n audit and live retranslate that preserves selection state.
3. Absolute artifact path in normal header — moved to Technical Details / export clipboard.

## Synthetic QA project

`workspaces/MLC1_Offline_Baselines_QA_8a22c20228f2`  
**SYNTHETIC QA DATA / NOT RESEARCH IONOGRAMS** (gitignored).

## Scenario A — blocked real pilot

1. Open a project without a frozen leakage-safe ML-B manifest.
2. Open **Offline ML Baselines**.
3. Expect readable blocker; Run remains disabled; no workaround; localization correct.

## Scenario B — new Majority Class after ML-C.1b (required)

1. Open synthetic QA project.
2. Do **not** treat historical experiments that contain prediction `m` as proof.
3. **New Experiment** → Majority Class → Validate Setup → Run Baseline.
4. Expect:
   - predictions contain a full valid morphology class (e.g. `mixed_spread`), never `m`;
   - confusion-matrix axes only valid morphology classes;
   - Development n=9; Overall agreement computed; Macro F1 number or localized N/A;
   - no raw `None` in normal UI;
   - Error Analysis rows show Item / Group / Expert reference / Date / Prediction / Correct?;
   - Holdout SEALED / UNUSED.
5. Optionally Verify Integrity on an old malformed experiment — expect invalid-label message; artifacts unchanged.

## Scenario C — new Nearest Centroid (required)

Same checks as Scenario B for label integrity and Error Analysis completeness.

## Scenario D — workflow / i18n (from ML-C.1a)

1. Completed result immutable; header has **no** absolute path.
2. RU↔EN preserves experiment / manifest / baseline / tab / layout.
3. No Not Responding; no lingering QThread.

## UI readability

Keep View / More / collapsible panels / column visibility / compact primary actions.

## After owner visual QA

- Full pytest (still deferred)
- README screenshot gallery refresh (deferred)
- Commit/push only when explicitly requested

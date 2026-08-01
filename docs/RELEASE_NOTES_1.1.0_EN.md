# Ionogram Morphology Lab 1.1.0

**Release date:** 2026-08-01  
**Russian name:** Лаборатория морфологии ионограмм

## Highlights

- Built-in MATLAB ionogram method library (`matlab_builtin`, 82 `.m` files) visible in MATLAB Studio
- Separate scientific outputs: layer, morphology, ambiguity, quality, parameters
- Scientific Rule Builder, Rule Testing Lab, versioned `.iml-rulepack` packs (9 built-in packs)
- Ionogram Parameters page with explicit implementation states
- Method Comparison and Pipeline Builder
- Es subtype source registry (no invented active letter list)
- Help expanded to 80 bilingual sections

## Packaging

Portable target: `dist\IonogramMorphologyLab\IonogramMorphologyLab.exe`  
Installer target (when Inno Setup available): `installer\IonogramMorphologyLab_Setup_1.1.0.exe`

## Scientific wording

Results remain **candidate morphology**. Methods do not confirm physical mechanisms from images alone. Development heuristics and synthetic tests are not scientific validation.

## External dependencies

- MATLAB Engine for Python optional
- External MATLAB `-batch` used when available (tested with R2019a where installed)
- Inno Setup optional for installer generation

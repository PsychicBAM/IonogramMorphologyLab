"""Bilingual CSV/JSON/HTML/Markdown reports — no causal claims from morphology alone."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ionogram_morphology_lab.utils.paths import ensure_dir


def export_run_reports(run_root: Path | str, language: str = "en") -> dict[str, str]:
    run_root = Path(run_root)
    pred_dir = run_root / "predictions"
    records = []
    for p in sorted(pred_dir.glob("*.json")):
        records.append(json.loads(p.read_text(encoding="utf-8")))

    out_dir = ensure_dir(run_root / "reports")
    exports = ensure_dir(run_root / "exports")

    # JSON dump
    json_path = exports / "results.json"
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    # CSV summary
    csv_path = exports / "results_summary.csv"
    fields = [
        "frame_id",
        "frame_index",
        "data_quality_status",
        "candidate_morphology",
        "final_auto_status",
        "top_alternative_1",
        "disagreement_flags",
        "possible_ox_confusion",
        "interference_status",
        "source_file_sha256",
        "profile_id",
        "profile_verification_status",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row = {k: r.get(k) for k in fields}
            row["disagreement_flags"] = "|".join(r.get("disagreement_flags") or [])
            w.writerow(row)

    md_path = out_dir / f"report_{language}.md"
    html_path = out_dir / f"report_{language}.html"
    md = _build_markdown(records, language)
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(_md_to_simple_html(md, language), encoding="utf-8")

    bib = out_dir / f"sources_{language}.md"
    sources = sorted(
        {
            f"{sid} p.{pg}"
            for r in records
            for sid, pg in zip(r.get("source_ids") or [], r.get("source_pages") or [])
        }
    )
    bib.write_text("\n".join(sources) or "(no sources activated)", encoding="utf-8")

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "markdown": str(md_path),
        "html": str(html_path),
        "bibliography": str(bib),
    }


def _build_markdown(records: list[dict[str, Any]], language: str) -> str:
    ru = language == "ru"
    title = "Отчёт анализа морфологии ионограмм" if ru else "Ionogram Morphology Analysis Report"
    lines = [
        f"# {title}",
        "",
        ("## 1. Техническое качество данных" if ru else "## 1. Technical data quality"),
    ]
    for r in records:
        lines.append(
            f"- `{r.get('frame_id')}`: {r.get('data_quality_status')} "
            f"(profile={r.get('profile_verification_status')})"
        )
    lines += ["", ("## 2. Видимая морфология" if ru else "## 2. Visible morphology")]
    for r in records:
        lines.append(
            f"- `{r.get('frame_id')}`: **{r.get('candidate_morphology')}** "
            f"[{r.get('final_auto_status')}]"
        )
    lines += [
        "",
        ("## 3. Автоматическая кандидатная категория" if ru else "## 3. Automatic candidate category"),
        ("Кандидатная морфология — не подтверждённый физический механизм."
         if ru
         else "Candidate morphology — not a confirmed physical mechanism."),
    ]
    lines += ["", ("## 4. Альтернативные интерпретации" if ru else "## 4. Alternative interpretations")]
    for r in records:
        alts = r.get("alternative_interpretations") or []
        if alts:
            lines.append(f"- `{r.get('frame_id')}`: {len(alts)} disagreement pair(s); flags={r.get('disagreement_flags')}")
        else:
            lines.append(f"- `{r.get('frame_id')}`: —")
    lines += ["", ("## 5. Сходство с эталонами" if ru else "## 5. Reference similarity")]
    for r in records:
        refs = r.get("nearest_references") or []
        if refs:
            top = refs[0]
            w = top.get("wording_ru") if ru else top.get("wording_en")
            lines.append(f"- `{r.get('frame_id')}`: {w} {top.get('citation')} (p.{top.get('source_page')})")
        else:
            lines.append(f"- `{r.get('frame_id')}`: (no packaged reference image; metadata match only)")
    lines += [
        "",
        ("## 6. Ограничения физического контекста" if ru else "## 6. Physical-context limitations"),
        (
            "Солнечные/dawn-dusk переменные не использовались для классификации морфологии."
            if ru
            else "Solar/dawn-dusk variables were not used for morphology classification."
        ),
        (
            "Номинальная виртуальная высота ≠ истинная высота."
            if ru
            else "Nominal virtual height ≠ true height."
        ),
        "",
        ("## 7. Решение эксперта" if ru else "## 7. Human expert decision"),
        ("Хранится отдельно от автоматического результата." if ru else "Stored separately from the automatic result."),
        "",
        ("## 8. Источники" if ru else "## 8. Sources used"),
    ]
    for r in records:
        for sid, pg in zip(r.get("source_ids") or [], r.get("source_pages") or []):
            lines.append(f"- {sid} p.{pg}")
    lines += [
        "",
        ("## 9. Воспроизводимость" if ru else "## 9. Reproducibility information"),
        f"- processing_version / rule_pack / reference_pack recorded per frame JSON",
        f"- n_frames={len(records)}",
        "",
        ("**Запрещённые формулировки не используются:** подтверждённый механизм, доказанная солнечная причина, RT-неустойчивость как вывод из одного кадра."
         if ru
         else "**Prohibited wording is not used:** confirmed mechanism, proved solar cause, RT instability from a single frame."),
    ]
    return "\n".join(lines) + "\n"


def _md_to_simple_html(md: str, language: str) -> str:
    # minimal conversion with escaping of user-controlled text
    import html as _html

    body = []
    for line in md.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{_html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{_html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body.append(f"<li>{_html.escape(line[2:])}</li>")
        elif line.strip() == "":
            body.append("<br/>")
        else:
            body.append(f"<p>{_html.escape(line)}</p>")
    title = _html.escape("IML Report")
    lang = _html.escape(language or "en")
    return (
        f"<!DOCTYPE html><html lang='{lang}'><head><meta charset='utf-8'>"
        f"<title>{title}</title></head><body>{''.join(body)}</body></html>"
    )

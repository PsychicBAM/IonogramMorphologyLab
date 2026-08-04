"""Human-readable Feature Diagnostics summary (shadow-only; no morphology)."""

from __future__ import annotations

from typing import Any


FEATURE_GROUPS: list[tuple[str, str, str, tuple[str, ...]]] = [
    # key, ru, en, id prefixes / exact ids
    ("summary", "Сводка", "Summary", ("v2_quality", "v2_trace_found", "v2_accepted")),
    ("quality", "Качество", "Quality", ("v2_quality", "v2_signal", "v2_snr", "v2_coverage")),
    ("trace", "След", "Trace", ("v2_trace", "v2_centerline", "v2_continuity", "v2_gap")),
    ("interference", "Помехи", "Interference", ("v2_interference", "v2_rfi", "v2_excl")),
    ("width_freq", "Ширина по оси частоты", "Frequency-axis width", ("v2_width_h", "v2_horizontal", "v2_axis_h")),
    ("width_height", "Ширина по оси высоты", "Height-axis width", ("v2_width_v", "v2_vertical", "v2_axis_v")),
    ("width_normal", "Ширина по нормали", "Normal width", ("v2_width_n", "v2_normal", "v2_orthogonal")),
    ("branches", "Ветви", "Branches", ("v2_branch", "v2_component", "v2_overseg")),
    ("temporal", "Временные признаки", "Temporal features", ("v2_temporal", "v2_time", "v2_frame_delta")),
    ("invalid", "Недействительные измерения", "Invalid measurements", ()),
    ("technical", "Технические сведения", "Technical details", ("v2_axis_tangent", "v2_processing")),
]


def group_for_feature(feature_id: str, valid: bool) -> str:
    if not valid:
        return "invalid"
    fid = feature_id.lower()
    for key, _ru, _en, prefixes in FEATURE_GROUPS:
        if key in ("summary", "invalid", "technical"):
            continue
        if any(fid.startswith(p) or p in fid for p in prefixes):
            return key
    if "tangent" in fid or "processing" in fid or "elapsed" in fid:
        return "technical"
    return "technical"


def group_title(key: str, language: str) -> str:
    for k, ru, en, _ in FEATURE_GROUPS:
        if k == key:
            return ru if language == "ru" else en
    return key


def _feat(result: Any, *candidates: str):
    feats = getattr(result, "features", {}) or {}
    for c in candidates:
        if c in feats:
            return feats[c]
        for k, v in feats.items():
            if c in k:
                return v
    return None


def _val(f: Any) -> str:
    if f is None:
        return "—"
    v = getattr(f, "value", None)
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}".replace(".", ",")
    return str(v)


def build_human_summary(
    result: Any,
    *,
    language: str,
    mat_name: str,
    frame: int,
    feature_version: str,
) -> str:
    ru = language == "ru"
    feats = getattr(result, "features", {}) or {}
    n_branches = len(getattr(result, "centerlines", None) or [])
    decisions = getattr(result, "component_decisions", None) or {}
    floor_rej = int(decisions.get("floor_rejected", decisions.get("floor_components_rejected", 0)) or 0)
    if floor_rej == 0:
        # try feature
        ff = _feat(result, "v2_floor_rejection_count", "floor_rejected")
        if ff is not None and getattr(ff, "value", None) is not None:
            try:
                floor_rej = int(ff.value)
            except (TypeError, ValueError):
                pass
    overseg = bool(getattr(result, "oversegmentation_suspected", False))
    quality = str(getattr(result, "quality_status", "") or "—")

    accepted = n_branches > 0
    trace_state = "yes" if accepted else "no"
    # Uncertain if quality suggests it
    if "uncertain" in quality.lower() or "low" in quality.lower():
        if accepted:
            trace_state = "uncertain"

    h_feat = _feat(result, "v2_width_h_median", "v2_horizontal_width_median", "v2_width_horizontal")
    v_feat = _feat(result, "v2_width_v_median", "v2_vertical_width_median", "v2_width_vertical")
    inter_feat = _feat(result, "v2_interference_fraction", "v2_interference_level")

    def axis_line(feat: Any, axis_ru: str, axis_en: str) -> str:
        if feat is None:
            return f"{axis_ru if ru else axis_en}: {'недоступно' if ru else 'unavailable'}"
        if not getattr(feat, "valid", True):
            reason = getattr(feat, "reason_invalid", "") or ""
            reason_txt = reason
            if reason == "axis_tangent_to_trace":
                reason_txt = (
                    "ось измерения совпадает с направлением следа"
                    if ru
                    else "measurement axis aligns with the trace direction"
                )
            return (
                f"{axis_ru}: недоступно — {reason_txt}"
                if ru
                else f"{axis_en}: unavailable — {reason_txt}"
            )
        unit = getattr(feat, "unit", "bins") or "bins"
        return (
            f"{axis_ru}: {_val(feat)} {unit}"
            if ru
            else f"{axis_en}: {_val(feat)} {unit}"
        )

    inter_level = _val(inter_feat)
    if ru:
        lines = [
            "Что сделала диагностика",
            f"Вход: {mat_name}, кадр {frame}.",
            f"Статус качества: {quality}.",
            f"След найден: {'да' if trace_state == 'yes' else 'нет' if trace_state == 'no' else 'неуверенно'}.",
            f"Принятых ветвей: {n_branches}.",
            f"Уровень помех: {inter_level}.",
            f"Компонентов отклонено как нижняя засветка: {floor_rej}.",
            f"Подозрение на пересегментацию: {'да' if overseg else 'нет'}.",
            axis_line(h_feat, "Горизонтальное измерение (ось частоты)", "H"),
            axis_line(v_feat, "Вертикальное измерение (ось высоты)", "V"),
            "Временные признаки: недоступны в покадровом режиме."
            if not any("temporal" in k for k in feats)
            else "Временные признаки: доступны.",
            f"Версия признаков: {feature_version}.",
            "Теневой режим: этот результат НЕ назначает морфологию и не участвует в классификации RuleEngine.",
        ]
        if n_branches:
            lines.insert(
                4,
                f"Выделены {n_branches} кандидатные ветви.",
            )
        if floor_rej:
            lines.insert(6, f"{floor_rej} компонентов отклонены как нижняя засветка.")
        if overseg:
            lines.append("Обнаружена возможная переcегментация — результат требует проверки.")
        if not accepted:
            lines.append("Надёжный след не найден. Это результат воздержания, а не ошибка.")
    else:
        lines = [
            "What the diagnostics did",
            f"Input: {mat_name}, frame {frame}.",
            f"Quality status: {quality}.",
            f"Trace found: {trace_state}.",
            f"Accepted branches: {n_branches}.",
            f"Interference level: {inter_level}.",
            f"Floor components rejected: {floor_rej}.",
            f"Oversegmentation suspected: {'yes' if overseg else 'no'}.",
            axis_line(h_feat, "H", "Horizontal (frequency-axis) measurement"),
            axis_line(v_feat, "V", "Vertical (height-axis) measurement"),
            "Temporal features: unavailable in single-frame mode."
            if not any("temporal" in k for k in feats)
            else "Temporal features: available.",
            f"Feature version: {feature_version}.",
            "Shadow mode: this result does NOT assign morphology and does not participate in RuleEngine classification.",
        ]
        if not accepted:
            lines.append("No reliable trace found. This is an abstention, not an error.")
        if overseg:
            lines.append("Possible oversegmentation detected — review required.")
    return "\n".join(lines)


def explain_feature_human(feature_id: str, feature: Any, language: str, registry_text: str) -> str:
    ru = language == "ru"
    valid = bool(getattr(feature, "valid", True))
    lines = [
        registry_text.strip(),
        "",
        f"{'Значение' if ru else 'Value'}: {getattr(feature, 'value', None)}",
        f"{'Единица' if ru else 'Unit'}: {getattr(feature, 'unit', '') or '—'}",
        f"{'Действительно' if ru else 'Valid'}: {'да' if valid else 'нет'}"
        if ru
        else f"Valid: {'yes' if valid else 'no'}",
    ]
    if not valid:
        lines.append(
            f"{'Причина' if ru else 'Reason invalid'}: {getattr(feature, 'reason_invalid', '') or '—'}"
        )
    region = getattr(feature, "affected_region", "") or ""
    if region:
        lines.append(f"{'Область' if ru else 'Affected region'}: {region}")
    lines.append(
        "Этот признак не участвует в текущей классификации."
        if ru
        else "This feature does not participate in the current classification."
    )
    lines.append(f"\n{'Технический ID' if ru else 'Technical ID'}: {feature_id}")
    return "\n".join(lines)


def run_state_message(state: str, language: str, detail: str = "") -> str:
    ru = language == "ru"
    messages = {
        "no_project": ("Проект не открыт.", "No project is open."),
        "no_active": (
            "Активный источник не выбран.",
            "No active source is selected.",
        ),
        "incompatible": (
            localize_role_message_safe(language),
            localize_role_message_safe(language),
        ),
        "loading": ("Загрузка кадра…", "Loading frame…"),
        "frame_ready": (
            "Кадр загружен. Нажмите «Запустить V2 (теневой режим)», чтобы построить диагностические маски.",
            'Frame loaded — V2 has not been run yet. Click "Run V2 (shadow)" to build diagnostic masks.',
        ),
        "v2_running": ("Выполняется Feature Pipeline V2…", "Feature Pipeline V2 is running…"),
        "v2_done": (
            "Анализ завершён. Над исходной ионограммой показаны выбранные слои.",
            "Analysis complete. Selected layers are shown over the source ionogram.",
        ),
        "v2_no_trace": (
            "Надёжный след не найден. Это результат воздержания, а не ошибка.",
            "No reliable trace found. This is an abstention, not an error.",
        ),
        "v2_uncertain": (
            "Анализ завершён с неуверенной геометрией. Проверьте слои и сводку.",
            "Analysis completed with uncertain geometry. Review layers and summary.",
        ),
        "v2_failed": (
            f"Диагностическая отрисовка не выполнена: {detail}" if detail else "Диагностическая отрисовка не выполнена.",
            f"Diagnostic rendering failed: {detail}" if detail else "Diagnostic rendering failed.",
        ),
        "blank_guard": (
            "Состояние не определено — обновите источник.",
            "Undefined state — refresh the source.",
        ),
    }
    pair = messages.get(state, messages["blank_guard"])
    return pair[0] if ru else pair[1]


def localize_role_message_safe(language: str) -> str:
    from ionogram_morphology_lab.ui.source_roles import localize_role_message

    return localize_role_message("missing_amp_all", language)

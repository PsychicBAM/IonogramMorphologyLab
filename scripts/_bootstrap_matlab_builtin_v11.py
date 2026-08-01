#!/usr/bin/env python3
"""Regenerate the built-in, candidate-only MATLAB/Octave ionogram library."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "matlab_builtin"

METHODS = {
    "core": [
        "iml_load_frame", "iml_load_sequence", "iml_validate_frame",
        "iml_export_result",
    ],
    "rendering": [
        "iml_render_raw_ionogram", "iml_render_sequence",
        "iml_create_contact_sheet",
    ],
    "trace_detection": [
        "iml_estimate_background", "iml_trace_global_threshold",
        "iml_trace_adaptive_threshold", "iml_trace_ridge_candidate",
        "iml_trace_connected_components", "iml_trace_continuity_filter",
        "iml_trace_skeleton", "iml_extract_branches",
        "iml_compare_trace_methods",
    ],
    "layer_detection": [
        "iml_detect_e_layer_candidate", "iml_estimate_foE_candidate",
        "iml_estimate_hE_prime_candidate", "iml_detect_e_es_overlap",
    ],
    "es_analysis": [
        "iml_detect_es_candidate", "iml_segment_es_trace",
        "iml_estimate_foEs_candidate", "iml_estimate_hEs_prime_candidate",
        "iml_estimate_fbEs_candidate", "iml_compare_e_and_es",
        "iml_es_temporal_persistence", "iml_classify_es_subtype_candidate",
    ],
    "f_layer_analysis": [
        "iml_detect_f1_candidate", "iml_detect_f2_candidate",
        "iml_detect_f_unspecified", "iml_separate_f1_f2_candidate",
        "iml_estimate_foF1_candidate", "iml_estimate_foF2_candidate",
        "iml_estimate_fxF2_candidate", "iml_estimate_hF1_prime_candidate",
        "iml_estimate_hF2_prime_candidate", "iml_f_layer_temporal_tracking",
    ],
    "spread_f_analysis": [
        "iml_detect_frequency_spread_candidate",
        "iml_detect_range_spread_candidate", "iml_detect_mixed_spread_candidate",
        "iml_detect_unspecified_spread_f_candidate",
        "iml_compare_clean_and_diffuse_trace",
        "iml_spread_f_temporal_persistence", "iml_spread_f_onset_candidate",
        "iml_spread_f_termination_candidate", "iml_spread_f_transition_candidate",
    ],
    "interference": [
        "iml_detect_vertical_interference", "iml_detect_horizontal_interference",
        "iml_detect_broadband_noise", "iml_detect_isolated_spikes",
        "iml_interference_temporal_persistence",
        "iml_trace_interference_separability",
    ],
    "branch_analysis": [
        "iml_count_trace_branches", "iml_measure_branch_separation",
        "iml_measure_branch_parallelism", "iml_compare_branch_diffuseness",
        "iml_detect_possible_ox_pattern",
        "iml_detect_possible_multiple_reflection",
    ],
    "temporal_analysis": [
        "iml_temporal_frame_difference", "iml_temporal_echo_persistence",
        "iml_temporal_candidate_summary",
    ],
    "parameters": [
        "iml_estimate_candidate_frequency", "iml_estimate_candidate_range",
        "iml_measure_candidate_snr",
    ],
    "comparison": [
        "iml_compare_candidate_masks", "iml_compare_candidate_frames",
    ],
    "reports": [
        "iml_build_candidate_report", "iml_write_candidate_summary",
    ],
    "examples": [
        "iml_example_end_to_end", "iml_example_sequence_review",
    ],
    "tests": [
        "iml_test_synthetic_trace", "iml_test_synthetic_layers",
    ],
}

OTHER = [
    "iml_detect_multiple_hop_candidate", "iml_detect_multiple_reflection_candidate",
    "iml_detect_overlapping_layers", "iml_detect_spread_e_candidate",
    "iml_detect_no_echo_condition", "iml_detect_low_signal",
    "iml_detect_saturation", "iml_detect_equipment_artifact",
    "iml_detect_unclassified_structure",
]
METHODS["layer_detection"].extend(OTHER)

HEADER = """\
% {upper}
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU: Только кандидатный, не причинный метод для разработки/обучения. Результат
% зависит от выбранного профиля ионограммы, калибровки, предобработки и порогов.
% Ограничения: это эвристическая диагностика, не верифицированная геофизическая
% интерпретация и не утверждение об истинной высоте слоя.
"""

def q(value: str) -> str:
    return value.replace("'", "''")


def generic_method(name: str, folder: str) -> str:
    """A self-contained base-MATLAB candidate detector/measurement."""
    domain = ""
    lname = name.lower()
    if any(x in lname for x in ("_e_", "foe", "he_prime", "hes", "foes", "fbes", "spread_e")):
        domain = """\
% Provisional E/Es display-domain band: fraction of the range axis, profile-dependent.
band_fraction = [0.05 0.45]; % Not a claim about true height.
"""
    elif any(x in lname for x in ("f1", "f2", "spread_f", "ox_pattern")):
        domain = """\
% Provisional F display-domain band: fraction of the range axis, profile-dependent.
band_fraction = [0.35 1.00]; % Not a claim about true height.
"""
    else:
        domain = "band_fraction = [0.00 1.00]; % Provisional display-domain selection.\n"
    status = "candidate"
    if name == "iml_classify_es_subtype_candidate":
        return es_classifier(name)
    if "temporal" in name or "persistence" in name or "tracking" in name or "onset" in name or "termination" in name or "transition" in name:
        return temporal_method(name)
    if name.startswith("iml_measure_") or name.startswith("iml_count_") or name.startswith("iml_compare_") or name.startswith("iml_estimate_fo") or name.startswith("iml_estimate_h") or name.startswith("iml_estimate_fx"):
        return measurement_method(name, domain)
    if name.startswith("iml_detect_no_echo"):
        return no_echo_method(name)
    if name.startswith("iml_detect_saturation"):
        return saturation_method(name)
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}{domain}frame = local_frame(varargin);
        [ok, message] = local_valid(frame);
        if ~ok, error('{name}:invalidFrame', '%s', message); end
        freq = local_axis('frequency', size(frame, 2));
        range = local_axis('range', size(frame, 1));
        X = double(frame); X(~isfinite(X)) = 0;
        lo = prctile(X(:), 5); hi = prctile(X(:), 99);
        if hi <= lo, hi = lo + 1; end
        N = min(1, max(0, (X - lo) / (hi - lo)));
        r1 = max(1, floor(band_fraction(1) * size(N,1)) + 1);
        r2 = min(size(N,1), ceil(band_fraction(2) * size(N,1)));
        mask = false(size(N)); roi = N(r1:r2,:); mask(r1:r2,:) = roi >= prctile(roi(:), 85);
        % Remove isolated bins using base-MATLAB convolution (no toolbox required).
        mask = mask & conv2(double(mask), ones(3), 'same') >= 3;
        score = sum(mask(:)) / numel(mask);
        result = struct('method', '{name}', 'status', '{status}', ...
          'score', score, 'mask', mask, 'frequency_axis', freq, ...
          'range_axis', range, 'band_fraction', band_fraction);
        iml_register_feature('{name}_coverage', score, 'fraction');
        iml_register_candidate_result('{name}', 'candidate', ...
          'Heuristic profile-dependent candidate; non-causal.');
        iml_add_provenance('{name}', 'v11 built-in heuristic');
        if score < 0.002, iml_add_warning('{name}: weak candidate or no echo.'); end
        iml_save_matrix('{name}_mask', double(mask));
        end

        function frame = local_frame(args)
        if ~isempty(args) && isnumeric(args{{1}}), frame = args{{1}}; else, frame = iml_get_current_frame(); end
        end

        function [ok, message] = local_valid(frame)
        ok = isnumeric(frame) && ismatrix(frame) && ~isempty(frame) && all(size(frame) >= [2 2]);
        if ok, message = ''; else, message = 'Frame must be a nonempty numeric 2-D matrix.'; end
        end

        function axis_values = local_axis(kind, n)
        if strcmp(kind, 'frequency'), axis_values = iml_get_frequency_axis(); else, axis_values = iml_get_range_axis(); end
        if ~isnumeric(axis_values) || numel(axis_values) ~= n, axis_values = 1:n; end
        axis_values = axis_values(:)';
        end
    """)


def measurement_method(name: str, domain: str) -> str:
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}{domain}if ~isempty(varargin) && isnumeric(varargin{{1}}), frame = varargin{{1}}; else, frame = iml_get_current_frame(); end
        if ~isnumeric(frame) || ~ismatrix(frame) || isempty(frame), error('{name}:invalidFrame', 'Expected a numeric 2-D frame.'); end
        X = double(frame); X(~isfinite(X)) = 0;
        lo = prctile(X(:), 5); hi = prctile(X(:), 99); if hi <= lo, hi = lo + 1; end
        N = min(1, max(0, (X - lo) / (hi - lo)));
        r1 = max(1, floor(band_fraction(1)*size(N,1))+1); r2 = min(size(N,1), ceil(band_fraction(2)*size(N,1)));
        roi = N(r1:r2,:); profile = max(roi, [], 1); [value, column] = max(profile);
        freq = iml_get_frequency_axis(); if numel(freq) ~= size(N,2), freq = 1:size(N,2); end
        range = iml_get_range_axis(); if numel(range) ~= size(N,1), range = 1:size(N,1); end
        [~, local_row] = max(roi(:,column)); row = r1 + local_row - 1;
        result = struct('method', '{name}', 'status', 'candidate', 'value', value, ...
          'frequency_candidate', freq(column), 'range_candidate', range(row), ...
          'column', column, 'row', row, 'band_fraction', band_fraction);
        iml_register_feature('{name}_value', value, 'normalized');
        iml_register_candidate_result('{name}', 'candidate', 'Profile-dependent heuristic measurement.');
        iml_add_provenance('{name}', 'v11 base MATLAB measurement');
        if value < 0.2, iml_add_warning('{name}: low-confidence measurement.'); end
        end
    """)


def no_echo_method(name: str) -> str:
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}if ~isempty(varargin) && isnumeric(varargin{{1}}), frame = varargin{{1}}; else, frame = iml_get_current_frame(); end
        if ~isnumeric(frame) || ~ismatrix(frame) || isempty(frame), error('{name}:invalidFrame', 'Expected a numeric 2-D frame.'); end
        X = double(frame); X(~isfinite(X)) = 0; dynamic_range = prctile(X(:),99) - prctile(X(:),1);
        coverage = mean(X(:) >= prctile(X(:),95));
        score = 1 / (1 + max(0, dynamic_range)) + max(0, 0.05 - coverage);
        result = struct('method','{name}','status','candidate','score',score,'dynamic_range',dynamic_range,'coverage',coverage);
        iml_register_feature('{name}_score', score, 'heuristic'); iml_register_candidate_result('{name}','candidate','No-echo heuristic only.');
        iml_add_provenance('{name}','v11 heuristic'); if score < 0.05, iml_add_warning('{name}: evidence does not support no-echo candidate.'); end
        end
    """)


def saturation_method(name: str) -> str:
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}if ~isempty(varargin) && isnumeric(varargin{{1}}), frame = varargin{{1}}; else, frame = iml_get_current_frame(); end
        if ~isnumeric(frame) || ~ismatrix(frame) || isempty(frame), error('{name}:invalidFrame', 'Expected a numeric 2-D frame.'); end
        X = double(frame); finite = X(isfinite(X)); if isempty(finite), finite = 0; end
        top = max(finite); mask = isfinite(X) & X >= top - max(eps(top), 1e-12); score = mean(mask(:));
        result = struct('method','{name}','status','candidate','score',score,'mask',mask,'maximum',top);
        iml_register_feature('{name}_coverage',score,'fraction'); iml_register_candidate_result('{name}','candidate','Digital clipping heuristic only.');
        iml_add_provenance('{name}','v11 saturation heuristic'); if score > 0.02, iml_add_warning('{name}: possible saturation; inspect instrument settings.'); end
        iml_save_matrix('{name}_mask',double(mask));
        end
    """)


def temporal_method(name: str) -> str:
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}if ~isempty(varargin) && iscell(varargin{{1}}), frames = varargin{{1}}; else, frames = iml_get_sequence(); end
        if ~iscell(frames), frames = {{frames}}; end
        n = numel(frames); coverage = zeros(1,n);
        for k = 1:n
          X = double(frames{{k}}); X(~isfinite(X)) = 0;
          if isempty(X), coverage(k) = 0; else, t = prctile(X(:),85); coverage(k) = mean(X(:) >= t); end
        end
        persistence = mean(coverage >= median(coverage));
        change = 0; if n > 1, change = mean(abs(diff(coverage))); end
        result = struct('method','{name}','status','candidate','frame_count',n,'coverage',coverage,'persistence',persistence,'change_rate',change);
        iml_register_feature('{name}_persistence',persistence,'fraction'); iml_register_candidate_result('{name}','candidate','Sequence heuristic; timing/profile dependent.');
        iml_add_provenance('{name}','v11 temporal heuristic'); if n < 2, iml_add_warning('{name}: sequence has fewer than two frames.'); end
        iml_save_matrix('{name}_coverage',coverage);
        end
    """)


def es_classifier(name: str) -> str:
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}% Safety default: subtype labels remain disabled until an external registry explicitly activates them.
        active = false; registry_file = 'iml_es_subtype_registry.mat';
        if exist(registry_file, 'file')
          S = load(registry_file);
          if isfield(S, 'es_subtype_classifier_active'), active = logical(S.es_subtype_classifier_active); end
        end
        result = struct('method','{name}','status','unverified','label','unverified/disabled','active',active);
        if active
          result.status = 'unverified'; result.label = 'unverified/disabled';
          iml_add_warning('{name}: registry is active, but built-in v11 deliberately abstains pending validation.');
        else
          iml_add_warning('{name}: subtype classifier disabled by default; returning abstention.');
        end
        iml_register_candidate_result('{name}','unverified','Abstained: no verified Es subtype classifier.');
        iml_add_provenance('{name}','v11 safety abstention');
        end
    """)


def special_method(name: str) -> str:
    if name == "iml_load_frame":
        return dedent(f"""\
            function frame = iml_load_frame(varargin)
            {HEADER.format(upper=name.upper())}if nargin == 0, frame = iml_get_current_frame(); return; end
            source = varargin{{1}};
            if isnumeric(source), frame = source;
            elseif ischar(source) || isstring(source)
              S = load(char(source)); names = fieldnames(S); frame = [];
              for k=1:numel(names), v=S.(names{{k}}); if isnumeric(v) && ismatrix(v), frame=v; break; end, end
              if isempty(frame), error('iml_load_frame:noMatrix','No numeric 2-D matrix found.'); end
            else, error('iml_load_frame:invalidInput','Use a matrix or MAT file path.'); end
            iml_add_provenance('iml_load_frame','Loaded candidate input frame');
            end
        """)
    if name == "iml_load_sequence":
        return dedent(f"""\
            function frames = iml_load_sequence(varargin)
            {HEADER.format(upper=name.upper())}if nargin == 0, frames = iml_get_sequence(); elseif iscell(varargin{{1}}), frames = varargin{{1}}; else, frames = {{varargin{{1}}}}; end
            if ~iscell(frames), frames = {{frames}}; end
            for k=1:numel(frames), if ~isnumeric(frames{{k}}) || ~ismatrix(frames{{k}}), error('iml_load_sequence:invalidFrame','Every frame must be numeric and 2-D.'); end, end
            iml_register_feature('iml_load_sequence_frame_count',numel(frames),'frames'); iml_add_provenance('iml_load_sequence','Loaded sequence');
            end
        """)
    if name == "iml_validate_frame":
        return dedent(f"""\
            function result = iml_validate_frame(varargin)
            {HEADER.format(upper=name.upper())}if nargin && isnumeric(varargin{{1}}), frame=varargin{{1}}; else, frame=iml_get_current_frame(); end
            valid = isnumeric(frame) && ismatrix(frame) && ~isempty(frame) && all(size(frame)>1);
            finite_fraction = 0; if valid, finite_fraction=mean(isfinite(frame(:))); end
            result=struct('valid',valid,'size',size(frame),'finite_fraction',finite_fraction);
            iml_register_feature('iml_validate_frame_finite_fraction',finite_fraction,'fraction'); iml_add_provenance('iml_validate_frame','Base validation');
            if ~valid || finite_fraction < 0.95, iml_add_warning('iml_validate_frame: invalid or incomplete candidate frame.'); end
            end
        """)
    if name in ("iml_render_raw_ionogram", "iml_render_sequence", "iml_create_contact_sheet"):
        return render_method(name)
    if name == "iml_export_result":
        return dedent(f"""\
            function output_file = iml_export_result(result, varargin)
            {HEADER.format(upper=name.upper())}if nargin < 1, error('iml_export_result:missingResult','Supply a result struct or matrix.'); end
            if nargin > 1, output_file=varargin{{1}}; else, output_file='iml_candidate_export.mat'; end
            save(output_file,'result','-v7'); iml_add_provenance('iml_export_result',['Saved ' output_file]);
            end
        """)
    if name.startswith("iml_example_"):
        return example_method(name)
    if name.startswith("iml_test_"):
        return test_method(name)
    return generic_method(name, "")


def render_method(name: str) -> str:
    sequence = name != "iml_render_raw_ionogram"
    body = """\
if ~isempty(varargin) && isnumeric(varargin{1}), frames = {varargin{1}}; else, frames = iml_get_sequence(); end
if ~iscell(frames), frames = {frames}; end
n = numel(frames); cols = ceil(sqrt(n)); rows = ceil(n/cols);
figure('Visible','off'); for k=1:n
  subplot(rows,cols,k); imagesc(frames{k}); axis xy; xlabel('Frequency bin'); ylabel('Range bin'); title(sprintf('Frame %d',k));
end
colormap('parula'); iml_save_plot('""" + name + """'); result=struct('method','""" + name + """','frame_count',n);
"""
    if not sequence:
        body = """\
if ~isempty(varargin) && isnumeric(varargin{1}), frame=varargin{1}; else, frame=iml_get_current_frame(); end
if ~isnumeric(frame) || ~ismatrix(frame), error('""" + name + """:invalidFrame','Expected numeric 2-D frame.'); end
freq=iml_get_frequency_axis(); range=iml_get_range_axis(); if numel(freq)~=size(frame,2), freq=1:size(frame,2); end; if numel(range)~=size(frame,1), range=1:size(frame,1); end
figure('Visible','off'); imagesc(freq,range,frame); axis xy; xlabel('Frequency'); ylabel('Range'); title('Raw ionogram (candidate display)'); colorbar; iml_save_plot('""" + name + """');
result=struct('method','""" + name + """','frequency_axis',freq,'range_axis',range);
"""
    return "function result = " + name + "(varargin)\n" + HEADER.format(upper=name.upper()) + body + "iml_add_provenance('" + name + "','Rendered candidate display');\nend\n"


def example_method(name: str) -> str:
    return dedent(f"""\
        function result = {name}(varargin)
        {HEADER.format(upper=name.upper())}if nargin && isnumeric(varargin{{1}}), frame=varargin{{1}}; else
          [c,r]=meshgrid(1:160,1:120); frame=0.08*rand(size(c))+exp(-((r-45-0.12*c).^2)/20);
        end
        validation=iml_validate_frame(frame); trace=iml_trace_global_threshold(frame); layer=iml_detect_f2_candidate(frame);
        result=struct('validation',validation,'trace',trace,'layer',layer); iml_register_candidate_result('{name}','example','Synthetic demonstration completed.');
        end
    """)


def test_method(name: str) -> str:
    return dedent(f"""\
        function passed = {name}()
        {HEADER.format(upper=name.upper())}rng(11); [c,r]=meshgrid(1:80,1:60); frame=0.02*rand(size(c))+exp(-((r-20-0.2*c).^2)/8);
        candidate=iml_trace_global_threshold(frame); passed=isstruct(candidate) && isfield(candidate,'mask') && any(candidate.mask(:));
        if ~passed, error('{name}:failed','Synthetic-only candidate test failed.'); end
        iml_add_provenance('{name}','Synthetic-only test; not scientific validation.');
        end
    """)


def manifest(folder: str, methods: list[str]) -> str:
    ids = "\n".join(f"  - {method}" for method in methods)
    return f"""plugin_id: builtin_{folder}_v11
name_en: Built-in candidate library: {folder}
name_ru: Встроенная кандидатная библиотека: {folder}
description_en: Development and teaching heuristics; not causal or scientifically verified.
description_ru: Эвристики для разработки и обучения; не причинные и не научно верифицированные.
version: 11.0.0
author: IonogramMorphologyLab
entrypoint: {methods[0]}.m
script_type: frame_analysis
supported_profiles:
  - "*"
MATLAB_release: R2019a
Octave_compatible: true
required_toolboxes: []
scientific_status: teaching
limitations_en: Profile-dependent candidate methods only; no true-height or causal claims.
limitations_ru: Только профиль-зависимые кандидатные методы; без утверждений об истинной высоте или причинности.
methods:
{ids}
"""


def write_docs() -> None:
    names = sum(METHODS.values(), [])
    (OUT / "README_EN.md").write_text(f"""# MATLAB built-in ionogram method library

This regenerated v11 library contains **{len(names)} executable candidate methods** for MATLAB R2019a and GNU Octave. It uses only base-language operations where practical and calls the `matlab_helpers/` bridge APIs for current frames, axes, provenance, warnings, result registration, matrices, and plots.

All methods are development/teaching heuristics. They are profile-dependent, non-causal, and are not validated measurements of physical layer height. E/Es/F display-domain selections are deliberately parameterized inside applicable methods.

Run `python scripts/_bootstrap_matlab_builtin_v11.py` from the repository root to regenerate the library. See `tests/README.md` for the synthetic-only test boundary.
""", encoding="utf-8")
    (OUT / "README_RU.md").write_text(f"""# Встроенная MATLAB-библиотека методов ионограмм

Эта регенерируемая библиотека v11 содержит **{len(names)} исполняемых кандидатных методов** для MATLAB R2019a и GNU Octave. По возможности используются базовые операции MATLAB/Octave и API из `matlab_helpers/`.

Все методы — эвристики для разработки и обучения. Они зависят от профиля, не являются причинными и не дают верифицированных физических высот слоёв. Выбор отображаемых диапазонов E/Es/F параметризован внутри соответствующих методов.

Для регенерации запустите `python scripts/_bootstrap_matlab_builtin_v11.py` из корня репозитория. Граница синтетической валидации описана в `tests/README.md`.
""", encoding="utf-8")
    (OUT / "tests" / "README.md").write_text("""# Synthetic-only validation

The MATLAB tests here create synthetic matrices and verify only that the candidate methods execute and produce structural outputs. They do not validate ionospheric physics, profile transferability, causal interpretation, or true-height estimates.
""", encoding="utf-8")


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    for folder, names in METHODS.items():
        target = OUT / folder
        target.mkdir(parents=True, exist_ok=True)
        for name in names:
            (target / f"{name}.m").write_text(special_method(name), encoding="utf-8", newline="\n")
    manifests = OUT / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    for folder, names in METHODS.items():
        (manifests / f"{folder}.iml-matlab.yaml").write_text(manifest(folder, names), encoding="utf-8", newline="\n")
    write_docs()
    print("MATLAB built-in v11 regenerated")
    for folder in METHODS:
        print(f"{folder}: {len(list((OUT / folder).glob('*.m')))} .m files")
    print(f"total: {len(list(OUT.glob('**/*.m')))} .m files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

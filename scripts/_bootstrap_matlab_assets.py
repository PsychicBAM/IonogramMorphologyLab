"""Create MATLAB helper .m files and teaching templates for v1.0."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS = ROOT / "matlab_helpers"
TEACH = ROOT / "matlab_studio_library" / "teaching"
TEMPL = ROOT / "matlab_studio_library" / "templates"

HELPER_CODE = {
    "iml_get_current_frame.m": r"""
function frame = iml_get_current_frame()
%IML_GET_CURRENT_FRAME Return current ionogram frame from bridge MAT.
if exist('iml_current_frame','var')
  frame = iml_current_frame; return;
end
S = load('iml_bridge_inputs.mat');
frame = S.iml_current_frame;
end
""".strip(),
    "iml_get_selected_frames.m": r"""
function frames = iml_get_selected_frames()
S = load('iml_bridge_inputs.mat');
if isfield(S,'iml_selected_frames')
  frames = S.iml_selected_frames;
else
  frames = S.iml_current_frame;
end
end
""".strip(),
    "iml_get_sequence.m": r"""
function frames = iml_get_sequence()
frames = iml_get_selected_frames();
end
""".strip(),
    "iml_get_frequency_axis.m": r"""
function ff = iml_get_frequency_axis()
S = load('iml_bridge_inputs.mat');
ff = S.iml_frequency_axis;
end
""".strip(),
    "iml_get_range_axis.m": r"""
function hh = iml_get_range_axis()
S = load('iml_bridge_inputs.mat');
hh = S.iml_range_axis;
end
""".strip(),
    "iml_get_profile.m": r"""
function profile = iml_get_profile()
meta = jsondecode(fileread('iml_metadata.json'));
profile = meta.profile;
end
""".strip(),
    "iml_get_metadata.m": r"""
function meta = iml_get_metadata()
meta = jsondecode(fileread('iml_metadata.json'));
end
""".strip(),
    "iml_report_progress.m": r"""
function iml_report_progress(percent, message)
fid = fopen('iml_progress.txt','a');
fprintf(fid, '%.1f\t%s\n', percent, message);
fclose(fid);
end
""".strip(),
    "iml_save_matrix.m": r"""
function iml_save_matrix(name, matrix)
save(['out_' name '.mat'], 'matrix', '-v7');
end
""".strip(),
    "iml_save_plot.m": r"""
function iml_save_plot(name)
print(['out_' name '.png'], '-dpng');
end
""".strip(),
    "iml_save_table.m": r"""
function iml_save_table(name, T)
if istable(T)
  writetable(T, ['out_' name '.csv']);
else
  csvwrite(['out_' name '.csv'], T);
end
end
""".strip(),
    "iml_register_feature.m": r"""
function iml_register_feature(feature_id, value, units)
reg = {};
if exist('iml_registered_features.json','file')
  reg = jsondecode(fileread('iml_registered_features.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
item.id = feature_id; item.value = value; item.units = units;
reg{end+1} = item;
fid = fopen('iml_registered_features.json','w');
fwrite(fid, jsonencode(reg)); fclose(fid);
end
""".strip(),
    "iml_register_candidate_result.m": r"""
function iml_register_candidate_result(category, status, note)
reg = {};
if exist('iml_registered_candidates.json','file')
  reg = jsondecode(fileread('iml_registered_candidates.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
item.category = category; item.status = status; item.note = note;
reg{end+1} = item;
fid = fopen('iml_registered_candidates.json','w');
fwrite(fid, jsonencode(reg)); fclose(fid);
end
""".strip(),
    "iml_add_warning.m": r"""
function iml_add_warning(msg)
reg = {};
if exist('iml_warnings.json','file')
  reg = jsondecode(fileread('iml_warnings.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
reg{end+1} = msg;
fid = fopen('iml_warnings.json','w'); fwrite(fid, jsonencode(reg)); fclose(fid);
end
""".strip(),
    "iml_add_provenance.m": r"""
function iml_add_provenance(key, value)
reg = {};
if exist('iml_provenance.json','file')
  reg = jsondecode(fileread('iml_provenance.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
item.key = key; item.value = value; reg{end+1} = item;
fid = fopen('iml_provenance.json','w'); fwrite(fid, jsonencode(reg)); fclose(fid);
end
""".strip(),
}

EXAMPLES = {
    "ex01_load_frame": (
        "main.m",
        "% EXAMPLE / TEACHING — not scientifically validated\n"
        "frame = iml_get_current_frame();\n"
        "iml_save_matrix('frame', frame);\n"
        "iml_add_provenance('example','ex01_load_frame');\n",
    ),
    "ex02_plot_ionogram": (
        "main.m",
        "% EXAMPLE / TEACHING — not scientifically validated\n"
        "frame = iml_get_current_frame();\n"
        "ff = iml_get_frequency_axis();\n"
        "hh = iml_get_range_axis();\n"
        "imagesc(ff, hh, frame); axis xy; colormap jet;\n"
        "xlabel('Frequency, MHz'); ylabel('Nominal virtual height');\n"
        "title('EXAMPLE ionogram');\n"
        "iml_save_plot('ionogram');\n",
    ),
    "ex03_plot_sequence": (
        "main.m",
        "% EXAMPLE / TEACHING — sequence montage\n"
        "frames = iml_get_sequence();\n"
        "n = size(frames,1);\n"
        "for i=1:min(n,9)\n"
        "  subplot(3,3,i); imagesc(squeeze(frames(i,:,:))); axis xy; title(sprintf('#%d',i));\n"
        "end\n"
        "iml_save_plot('sequence');\n",
    ),
    "ex04_horizontal_projection": (
        "main.m",
        "% EXAMPLE / TEACHING — horizontal projection\n"
        "frame = iml_get_current_frame();\n"
        "hp = mean(frame, 1);\n"
        "plot(hp); title('Horizontal projection (teaching)');\n"
        "iml_save_matrix('hproj', hp); iml_save_plot('hproj');\n",
    ),
    "ex05_vertical_projection": (
        "main.m",
        "% EXAMPLE / TEACHING — vertical projection\n"
        "frame = iml_get_current_frame();\n"
        "vp = mean(frame, 2);\n"
        "plot(vp); title('Vertical projection (teaching)');\n"
        "iml_save_matrix('vproj', vp); iml_save_plot('vproj');\n",
    ),
    "ex06_vertical_interference": (
        "main.m",
        "% EXAMPLE / TEACHING — heuristic only\n"
        "frame = iml_get_current_frame();\n"
        "thr = prctile(frame(:), 92);\n"
        "bright = frame >= thr;\n"
        "colfrac = mean(bright, 1);\n"
        "n_stripes = sum(colfrac >= 0.55);\n"
        "iml_register_feature('full_height_stripe_count', n_stripes, 'count');\n"
        "iml_add_warning('Heuristic interference example — not validated');\n",
    ),
    "ex07_simple_trace_mask": (
        "main.m",
        "% EXAMPLE / TEACHING — simple threshold mask\n"
        "frame = iml_get_current_frame();\n"
        "mask = frame >= prctile(frame(:), 85);\n"
        "imagesc(mask); axis xy; title('Trace mask (teaching)');\n"
        "iml_save_matrix('trace_mask', double(mask)); iml_save_plot('trace_mask');\n",
    ),
    "ex08_compare_two": (
        "main.m",
        "% EXAMPLE / TEACHING — compare first two selected frames\n"
        "frames = iml_get_selected_frames();\n"
        "a = squeeze(frames(1,:,:));\n"
        "if size(frames,1) >= 2, b = squeeze(frames(2,:,:)); else, b = a; end\n"
        "d = abs(a-b);\n"
        "imagesc(d); axis xy; title('Absolute difference (teaching)');\n"
        "iml_register_feature('mean_abs_diff', mean(d(:)), 'arb');\n"
        "iml_save_plot('compare');\n",
    ),
    "ex09_export_feature_table": (
        "main.m",
        "% EXAMPLE / TEACHING — export CSV feature table\n"
        "frame = iml_get_current_frame();\n"
        "T = [mean(frame(:)), std(frame(:)), max(frame(:))];\n"
        "iml_save_table('features', T);\n"
        "iml_add_provenance('example','ex09_export_feature_table');\n",
    ),
    "ex10_register_feature": (
        "main.m",
        "% EXAMPLE / TEACHING\n"
        "frame = iml_get_current_frame();\n"
        "iml_register_feature('mean_amplitude', mean(frame(:)), 'arb');\n",
    ),
    "ex11_register_candidate": (
        "main.m",
        "% EXAMPLE / TEACHING — candidate only\n"
        "iml_register_candidate_result('abstain','example','Teaching demo — not a validated classifier');\n",
    ),
    "ex12_contact_sheet": (
        "main.m",
        "% EXAMPLE / TEACHING — contact sheet from selected frames\n"
        "frames = iml_get_selected_frames();\n"
        "n = min(size(frames,1), 25);\n"
        "for i=1:n\n"
        "  subplot(5,5,i); imagesc(squeeze(frames(i,:,:))); axis xy off;\n"
        "end\n"
        "iml_save_plot('contact_sheet');\n",
    ),
    "ex13_process_folder": (
        "main.m",
        "% EXAMPLE / TEACHING — folder processing is orchestrated by IML batch mode\n"
        "iml_report_progress(10, 'Folder jobs should be launched from MATLAB Studio run mode');\n"
        "iml_add_warning('Use IML run-on-folder; this script only records progress');\n"
        "iml_report_progress(100, 'done');\n",
    ),
    "ex14_save_figure_csv": (
        "main.m",
        "% EXAMPLE / TEACHING — save figure and CSV\n"
        "frame = iml_get_current_frame();\n"
        "imagesc(frame); axis xy; colormap jet; title('Teaching export');\n"
        "iml_save_plot('export_fig');\n"
        "iml_save_table('export_stats', [min(frame(:)), mean(frame(:)), max(frame(:))]);\n",
    ),
}


def main() -> None:
    HELPERS.mkdir(parents=True, exist_ok=True)
    TEACH.mkdir(parents=True, exist_ok=True)
    TEMPL.mkdir(parents=True, exist_ok=True)
    for name, code in HELPER_CODE.items():
        (HELPERS / name).write_text(code + "\n", encoding="utf-8")
    for sid, (ep, code) in EXAMPLES.items():
        d = TEACH / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / ep).write_text(code, encoding="utf-8")
        man = f"""plugin_id: {sid}
name_en: {sid}
name_ru: {sid}
description_en: Teaching example — not scientifically validated
description_ru: Учебный пример — не является научной валидацией
version: 1.0.0
entrypoint: {ep}
script_type: teaching_demo
scientific_status: teaching
Octave_compatible: true
limitations_en: Example/teaching only
limitations_ru: Только учебный пример
"""
        (d / f"{sid}.iml-matlab.yaml").write_text(man, encoding="utf-8")
    print(f"helpers={len(HELPER_CODE)} examples={len(EXAMPLES)}")


if __name__ == "__main__":
    main()

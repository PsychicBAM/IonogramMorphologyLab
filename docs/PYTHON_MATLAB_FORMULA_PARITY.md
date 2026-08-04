# Python / MATLAB Formula Parity (Phase 4A.1b)

Generated: `2026-08-02T18:51:34.097020+00:00`

**Current evidence:** `workspaces/_phase4a_parity/parity_report.json` (plus matlab stdout/stderr). This Markdown is a human mirror only.

**Counts:** total_cases=25; cross_runtime_cases=24; python_only_cases=1; matlab_only_cases=0; valid_cross_runtime_matches=8; invalid_cross_runtime_rejections=16

Do not describe all total_cases as Python↔MATLAB comparisons when python_only_cases > 0.

| Case | Kind | Runtime | Python | MATLAB | Pass |
|------|------|---------|--------|--------|------|
| vh_normal | valid | cross_runtime | valid=True / 149.896229 | 149.896229 | True |
| vh_zero | valid | cross_runtime | valid=True / None | 0.0 | True |
| mhz_first_bin | valid | cross_runtime | valid=True / 1.5 | 1.5 | True |
| mhz_final_bin | valid | cross_runtime | valid=True / 9.081 | 9.081 | True |
| h_nom_first | valid | cross_runtime | valid=True / None | 0.0 | True |
| h_nom_final | valid | cross_runtime | valid=True / 637.5 | 637.5 | True |
| width_normal | valid | cross_runtime | valid=True / 3 | 3.0 | True |
| width_zero_mask | valid | cross_runtime | valid=True / None | 0.0 | True |
| vh_nan | invalid | cross_runtime | valid=False / non_finite_group_delay | nan | True |
| vh_inf | invalid | cross_runtime | valid=False / non_finite_group_delay | nan | True |
| vh_negative | invalid | cross_runtime | valid=False / negative_group_delay | nan | True |
| mhz_negative_index | invalid | cross_runtime | valid=False / bin_out_of_range | nan | True |
| mhz_above_max | invalid | cross_runtime | valid=False / bin_out_of_range | nan | True |
| mhz_zero_axis_length | invalid | cross_runtime | valid=False / invalid_axis_parameters | nan | True |
| mhz_fractional_bin | invalid | cross_runtime | valid=False / fractional_or_float_bin_index | nan | True |
| mhz_boolean_bin | invalid | cross_runtime | valid=False / boolean_bin_index | nan | True |
| mhz_malformed_step | invalid | cross_runtime | valid=False / non_finite_axis_parameters | nan | True |
| h_nom_above_max | invalid | cross_runtime | valid=False / bin_out_of_range | nan | True |
| h_nom_fractional_bin | invalid | cross_runtime | valid=False / fractional_or_float_bin_index | nan | True |
| h_nom_boolean_bin | invalid | cross_runtime | valid=False / boolean_bin_index | nan | True |
| h_nom_zero_axis | invalid | cross_runtime | valid=False / invalid_axis_parameters | nan | True |
| width_empty | invalid | cross_runtime | valid=False / empty_input | nan | True |
| width_2d | invalid | cross_runtime | valid=False / wrong_dimensionality_requires_1d | nan | True |
| width_wrong_dim_3d | invalid | cross_runtime | valid=False / wrong_dimensionality_requires_1d | nan | True |
| vh_nonnumeric | invalid | python_only | valid=False / exception | None | True |

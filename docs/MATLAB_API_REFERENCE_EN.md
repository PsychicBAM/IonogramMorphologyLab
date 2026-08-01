# MATLAB Bridge API Reference

All helpers operate in the isolated MATLAB Studio run workspace. They are the supported interface between a script and Ionogram Morphology Lab 1.1.0; direct mutation of source MAT data is unsupported.

| Helper | Purpose |
|---|---|
| `iml_get_current_frame` | Return the selected frame matrix. |
| `iml_get_selected_frames` | Return the selected frame collection. |
| `iml_get_sequence` | Return the available sequence context. |
| `iml_get_frequency_axis` | Return the frequency coordinate vector. |
| `iml_get_range_axis` | Return the range/nominal virtual-height vector. |
| `iml_get_profile` | Return the instrument profile metadata. |
| `iml_get_metadata` | Return run, frame, and project metadata. |
| `iml_report_progress` | Publish bounded execution progress/message. |
| `iml_save_matrix` | Save a derived matrix artifact. |
| `iml_save_plot` | Save a figure artifact. |
| `iml_save_table` | Save a tabular artifact. |
| `iml_register_feature` | Register an interpretable feature and metadata. |
| `iml_register_candidate_result` | Register a candidate result, not an expert decision. |
| `iml_add_warning` | Register a quality or interpretation warning. |
| `iml_add_provenance` | Register method, parameter, and source provenance. |

## Usage rules
Read helpers may return empty data when the requested context was not provided. Check sizes, units, profile status, and missing values before calculation. Save helpers create derived output only. Registration helpers should include stable names, units where applicable, values, and meaningful warnings. Candidate results must preserve `confidence_score` as null when no calibrated confidence exists; do not fabricate a probability.

## Minimal example
```matlab
frame = iml_get_current_frame();
f = iml_get_frequency_axis();
metric = mean(frame(:), 'omitnan');
iml_register_feature('mean_amplitude', metric, 'a.u.');
iml_add_provenance('algorithm', 'mean_amplitude_v1');
iml_save_plot('mean_over_frequency', plot(f, mean(frame, 1)));
```

The exact helper signatures supplied with the installation are authoritative. Scripts must report failure rather than interpreting absent data as a positive scientific result.

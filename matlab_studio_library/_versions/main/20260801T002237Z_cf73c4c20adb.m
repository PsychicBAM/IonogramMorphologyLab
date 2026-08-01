% EXAMPLE / TEACHING — export CSV feature table
frame = iml_get_current_frame();
T = [mean(frame(:)), std(frame(:)), max(frame(:))];
iml_save_table('features', T);
iml_add_provenance('example','ex09_export_feature_table');

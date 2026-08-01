% EXAMPLE / TEACHING — simple threshold mask
frame = iml_get_current_frame();
mask = frame >= prctile(frame(:), 85);
imagesc(mask); axis xy; title('Trace mask (teaching)');
iml_save_matrix('trace_mask', double(mask)); iml_save_plot('trace_mask');

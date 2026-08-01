% EXAMPLE / TEACHING — save figure and CSV
frame = iml_get_current_frame();
imagesc(frame); axis xy; colormap jet; title('Teaching export');
iml_save_plot('export_fig');
iml_save_table('export_stats', [min(frame(:)), mean(frame(:)), max(frame(:))]);

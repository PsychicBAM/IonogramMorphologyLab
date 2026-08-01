% EXAMPLE / TEACHING — compare first two selected frames
frames = iml_get_selected_frames();
a = squeeze(frames(1,:,:));
if size(frames,1) >= 2, b = squeeze(frames(2,:,:)); else, b = a; end
d = abs(a-b);
imagesc(d); axis xy; title('Absolute difference (teaching)');
iml_register_feature('mean_abs_diff', mean(d(:)), 'arb');
iml_save_plot('compare');

% EXAMPLE / TEACHING — vertical projection
frame = iml_get_current_frame();
vp = mean(frame, 2);
plot(vp); title('Vertical projection (teaching)');
iml_save_matrix('vproj', vp); iml_save_plot('vproj');

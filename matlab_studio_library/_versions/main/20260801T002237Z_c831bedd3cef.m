% EXAMPLE / TEACHING — horizontal projection
frame = iml_get_current_frame();
hp = mean(frame, 1);
plot(hp); title('Horizontal projection (teaching)');
iml_save_matrix('hproj', hp); iml_save_plot('hproj');

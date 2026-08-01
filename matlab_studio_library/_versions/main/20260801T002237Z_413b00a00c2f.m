% EXAMPLE / TEACHING — heuristic only
frame = iml_get_current_frame();
thr = prctile(frame(:), 92);
bright = frame >= thr;
colfrac = mean(bright, 1);
n_stripes = sum(colfrac >= 0.55);
iml_register_feature('full_height_stripe_count', n_stripes, 'count');
iml_add_warning('Heuristic interference example — not validated');

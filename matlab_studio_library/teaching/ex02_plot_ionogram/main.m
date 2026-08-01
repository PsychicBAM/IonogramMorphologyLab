% EXAMPLE / TEACHING — not scientifically validated
frame = iml_get_current_frame();
ff = iml_get_frequency_axis();
hh = iml_get_range_axis();
imagesc(ff, hh, frame); axis xy; colormap jet;
xlabel('Frequency, MHz'); ylabel('Nominal virtual height');
title('EXAMPLE ionogram');
iml_save_plot('ionogram');

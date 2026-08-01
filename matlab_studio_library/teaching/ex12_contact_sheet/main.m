% EXAMPLE / TEACHING — contact sheet from selected frames
frames = iml_get_selected_frames();
n = min(size(frames,1), 25);
for i=1:n
  subplot(5,5,i); imagesc(squeeze(frames(i,:,:))); axis xy off;
end
iml_save_plot('contact_sheet');

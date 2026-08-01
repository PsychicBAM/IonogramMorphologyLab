% EXAMPLE / TEACHING — sequence montage
frames = iml_get_sequence();
n = size(frames,1);
for i=1:min(n,9)
  subplot(3,3,i); imagesc(squeeze(frames(i,:,:))); axis xy; title(sprintf('#%d',i));
end
iml_save_plot('sequence');

function frames = iml_get_selected_frames()
S = load('iml_bridge_inputs.mat');
if isfield(S,'iml_selected_frames')
  frames = S.iml_selected_frames;
else
  frames = S.iml_current_frame;
end
end

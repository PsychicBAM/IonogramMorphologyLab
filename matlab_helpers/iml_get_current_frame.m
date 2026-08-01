function frame = iml_get_current_frame()
%IML_GET_CURRENT_FRAME Return current ionogram frame from bridge MAT.
if exist('iml_current_frame','var')
  frame = iml_current_frame; return;
end
S = load('iml_bridge_inputs.mat');
frame = S.iml_current_frame;
end

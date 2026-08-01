function result = iml_create_contact_sheet(varargin)
% IML_CREATE_CONTACT_SHEET
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if ~isempty(varargin) && isnumeric(varargin{1}), frames = {varargin{1}}; else, frames = iml_get_sequence(); end
if ~iscell(frames), frames = {frames}; end
n = numel(frames); cols = ceil(sqrt(n)); rows = ceil(n/cols);
figure('Visible','off'); for k=1:n
  subplot(rows,cols,k); imagesc(frames{k}); axis xy; xlabel('Frequency bin'); ylabel('Range bin'); title(sprintf('Frame %d',k));
end
colormap('parula'); iml_save_plot('iml_create_contact_sheet'); result=struct('method','iml_create_contact_sheet','frame_count',n);
iml_add_provenance('iml_create_contact_sheet','Rendered candidate display');
end

function result = iml_render_raw_ionogram(varargin)
% IML_RENDER_RAW_IONOGRAM
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if ~isempty(varargin) && isnumeric(varargin{1}), frame=varargin{1}; else, frame=iml_get_current_frame(); end
if ~isnumeric(frame) || ~ismatrix(frame), error('iml_render_raw_ionogram:invalidFrame','Expected numeric 2-D frame.'); end
freq=iml_get_frequency_axis(); range=iml_get_range_axis(); if numel(freq)~=size(frame,2), freq=1:size(frame,2); end; if numel(range)~=size(frame,1), range=1:size(frame,1); end
figure('Visible','off'); imagesc(freq,range,frame); axis xy; xlabel('Frequency'); ylabel('Range'); title('Raw ionogram (candidate display)'); colorbar; iml_save_plot('iml_render_raw_ionogram');
result=struct('method','iml_render_raw_ionogram','frequency_axis',freq,'range_axis',range);
iml_add_provenance('iml_render_raw_ionogram','Rendered candidate display');
end

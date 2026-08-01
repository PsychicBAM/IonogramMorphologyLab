function frames = iml_load_sequence(varargin)
            % IML_LOAD_SEQUENCE
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if nargin == 0, frames = iml_get_sequence(); elseif iscell(varargin{1}), frames = varargin{1}; else, frames = {varargin{1}}; end
            if ~iscell(frames), frames = {frames}; end
            for k=1:numel(frames), if ~isnumeric(frames{k}) || ~ismatrix(frames{k}), error('iml_load_sequence:invalidFrame','Every frame must be numeric and 2-D.'); end, end
            iml_register_feature('iml_load_sequence_frame_count',numel(frames),'frames'); iml_add_provenance('iml_load_sequence','Loaded sequence');
            end

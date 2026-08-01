function result = iml_validate_frame(varargin)
            % IML_VALIDATE_FRAME
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if nargin && isnumeric(varargin{1}), frame=varargin{1}; else, frame=iml_get_current_frame(); end
            valid = isnumeric(frame) && ismatrix(frame) && ~isempty(frame) && all(size(frame)>1);
            finite_fraction = 0; if valid, finite_fraction=mean(isfinite(frame(:))); end
            result=struct('valid',valid,'size',size(frame),'finite_fraction',finite_fraction);
            iml_register_feature('iml_validate_frame_finite_fraction',finite_fraction,'fraction'); iml_add_provenance('iml_validate_frame','Base validation');
            if ~valid || finite_fraction < 0.95, iml_add_warning('iml_validate_frame: invalid or incomplete candidate frame.'); end
            end

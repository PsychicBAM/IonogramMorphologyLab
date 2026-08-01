function frame = iml_load_frame(varargin)
            % IML_LOAD_FRAME
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if nargin == 0, frame = iml_get_current_frame(); return; end
            source = varargin{1};
            if isnumeric(source), frame = source;
            elseif ischar(source) || isstring(source)
              S = load(char(source)); names = fieldnames(S); frame = [];
              for k=1:numel(names), v=S.(names{k}); if isnumeric(v) && ismatrix(v), frame=v; break; end, end
              if isempty(frame), error('iml_load_frame:noMatrix','No numeric 2-D matrix found.'); end
            else, error('iml_load_frame:invalidInput','Use a matrix or MAT file path.'); end
            iml_add_provenance('iml_load_frame','Loaded candidate input frame');
            end

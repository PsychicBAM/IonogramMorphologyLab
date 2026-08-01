function output_file = iml_export_result(result, varargin)
            % IML_EXPORT_RESULT
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if nargin < 1, error('iml_export_result:missingResult','Supply a result struct or matrix.'); end
            if nargin > 1, output_file=varargin{1}; else, output_file='iml_candidate_export.mat'; end
            save(output_file,'result','-v7'); iml_add_provenance('iml_export_result',['Saved ' output_file]);
            end

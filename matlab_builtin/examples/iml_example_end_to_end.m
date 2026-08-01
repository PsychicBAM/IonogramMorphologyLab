function result = iml_example_end_to_end(varargin)
        % IML_EXAMPLE_END_TO_END
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if nargin && isnumeric(varargin{1}), frame=varargin{1}; else
          [c,r]=meshgrid(1:160,1:120); frame=0.08*rand(size(c))+exp(-((r-45-0.12*c).^2)/20);
        end
        validation=iml_validate_frame(frame); trace=iml_trace_global_threshold(frame); layer=iml_detect_f2_candidate(frame);
        result=struct('validation',validation,'trace',trace,'layer',layer); iml_register_candidate_result('iml_example_end_to_end','example','Synthetic demonstration completed.');
        end

function result = iml_detect_no_echo_condition(varargin)
        % IML_DETECT_NO_ECHO_CONDITION
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if ~isempty(varargin) && isnumeric(varargin{1}), frame = varargin{1}; else, frame = iml_get_current_frame(); end
        if ~isnumeric(frame) || ~ismatrix(frame) || isempty(frame), error('iml_detect_no_echo_condition:invalidFrame', 'Expected a numeric 2-D frame.'); end
        X = double(frame); X(~isfinite(X)) = 0; dynamic_range = prctile(X(:),99) - prctile(X(:),1);
        coverage = mean(X(:) >= prctile(X(:),95));
        score = 1 / (1 + max(0, dynamic_range)) + max(0, 0.05 - coverage);
        result = struct('method','iml_detect_no_echo_condition','status','candidate','score',score,'dynamic_range',dynamic_range,'coverage',coverage);
        iml_register_feature('iml_detect_no_echo_condition_score', score, 'heuristic'); iml_register_candidate_result('iml_detect_no_echo_condition','candidate','No-echo heuristic only.');
        iml_add_provenance('iml_detect_no_echo_condition','v11 heuristic'); if score < 0.05, iml_add_warning('iml_detect_no_echo_condition: evidence does not support no-echo candidate.'); end
        end

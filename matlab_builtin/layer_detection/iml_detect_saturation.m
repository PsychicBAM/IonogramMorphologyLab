function result = iml_detect_saturation(varargin)
        % IML_DETECT_SATURATION
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if ~isempty(varargin) && isnumeric(varargin{1}), frame = varargin{1}; else, frame = iml_get_current_frame(); end
        if ~isnumeric(frame) || ~ismatrix(frame) || isempty(frame), error('iml_detect_saturation:invalidFrame', 'Expected a numeric 2-D frame.'); end
        X = double(frame); finite = X(isfinite(X)); if isempty(finite), finite = 0; end
        top = max(finite); mask = isfinite(X) & X >= top - max(eps(top), 1e-12); score = mean(mask(:));
        result = struct('method','iml_detect_saturation','status','candidate','score',score,'mask',mask,'maximum',top);
        iml_register_feature('iml_detect_saturation_coverage',score,'fraction'); iml_register_candidate_result('iml_detect_saturation','candidate','Digital clipping heuristic only.');
        iml_add_provenance('iml_detect_saturation','v11 saturation heuristic'); if score > 0.02, iml_add_warning('iml_detect_saturation: possible saturation; inspect instrument settings.'); end
        iml_save_matrix('iml_detect_saturation_mask',double(mask));
        end

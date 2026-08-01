function result = iml_estimate_fxF2_candidate(varargin)
        % IML_ESTIMATE_FXF2_CANDIDATE
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
% Provisional F display-domain band: fraction of the range axis, profile-dependent.
band_fraction = [0.35 1.00]; % Not a claim about true height.
if ~isempty(varargin) && isnumeric(varargin{1}), frame = varargin{1}; else, frame = iml_get_current_frame(); end
        if ~isnumeric(frame) || ~ismatrix(frame) || isempty(frame), error('iml_estimate_fxF2_candidate:invalidFrame', 'Expected a numeric 2-D frame.'); end
        X = double(frame); X(~isfinite(X)) = 0;
        lo = prctile(X(:), 5); hi = prctile(X(:), 99); if hi <= lo, hi = lo + 1; end
        N = min(1, max(0, (X - lo) / (hi - lo)));
        r1 = max(1, floor(band_fraction(1)*size(N,1))+1); r2 = min(size(N,1), ceil(band_fraction(2)*size(N,1)));
        roi = N(r1:r2,:); profile = max(roi, [], 1); [value, column] = max(profile);
        freq = iml_get_frequency_axis(); if numel(freq) ~= size(N,2), freq = 1:size(N,2); end
        range = iml_get_range_axis(); if numel(range) ~= size(N,1), range = 1:size(N,1); end
        [~, local_row] = max(roi(:,column)); row = r1 + local_row - 1;
        result = struct('method', 'iml_estimate_fxF2_candidate', 'status', 'candidate', 'value', value, ...
          'frequency_candidate', freq(column), 'range_candidate', range(row), ...
          'column', column, 'row', row, 'band_fraction', band_fraction);
        iml_register_feature('iml_estimate_fxF2_candidate_value', value, 'normalized');
        iml_register_candidate_result('iml_estimate_fxF2_candidate', 'candidate', 'Profile-dependent heuristic measurement.');
        iml_add_provenance('iml_estimate_fxF2_candidate', 'v11 base MATLAB measurement');
        if value < 0.2, iml_add_warning('iml_estimate_fxF2_candidate: low-confidence measurement.'); end
        end

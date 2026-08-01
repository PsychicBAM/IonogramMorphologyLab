function result = iml_detect_frequency_spread_candidate(varargin)
        % IML_DETECT_FREQUENCY_SPREAD_CANDIDATE
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
band_fraction = [0.00 1.00]; % Provisional display-domain selection.
frame = local_frame(varargin);
        [ok, message] = local_valid(frame);
        if ~ok, error('iml_detect_frequency_spread_candidate:invalidFrame', '%s', message); end
        freq = local_axis('frequency', size(frame, 2));
        range = local_axis('range', size(frame, 1));
        X = double(frame); X(~isfinite(X)) = 0;
        lo = prctile(X(:), 5); hi = prctile(X(:), 99);
        if hi <= lo, hi = lo + 1; end
        N = min(1, max(0, (X - lo) / (hi - lo)));
        r1 = max(1, floor(band_fraction(1) * size(N,1)) + 1);
        r2 = min(size(N,1), ceil(band_fraction(2) * size(N,1)));
        mask = false(size(N)); roi = N(r1:r2,:); mask(r1:r2,:) = roi >= prctile(roi(:), 85);
        % Remove isolated bins using base-MATLAB convolution (no toolbox required).
        mask = mask & conv2(double(mask), ones(3), 'same') >= 3;
        score = sum(mask(:)) / numel(mask);
        result = struct('method', 'iml_detect_frequency_spread_candidate', 'status', 'candidate', ...
          'score', score, 'mask', mask, 'frequency_axis', freq, ...
          'range_axis', range, 'band_fraction', band_fraction);
        iml_register_feature('iml_detect_frequency_spread_candidate_coverage', score, 'fraction');
        iml_register_candidate_result('iml_detect_frequency_spread_candidate', 'candidate', ...
          'Heuristic profile-dependent candidate; non-causal.');
        iml_add_provenance('iml_detect_frequency_spread_candidate', 'v11 built-in heuristic');
        if score < 0.002, iml_add_warning('iml_detect_frequency_spread_candidate: weak candidate or no echo.'); end
        iml_save_matrix('iml_detect_frequency_spread_candidate_mask', double(mask));
        end

function frame = local_frame(args)
        if ~isempty(args) && isnumeric(args{1}), frame = args{1}; else, frame = iml_get_current_frame(); end
        end

function [ok, message] = local_valid(frame)
        ok = isnumeric(frame) && ismatrix(frame) && ~isempty(frame) && all(size(frame) >= [2 2]);
        if ok, message = ''; else, message = 'Frame must be a nonempty numeric 2-D matrix.'; end
        end

function axis_values = local_axis(kind, n)
        if strcmp(kind, 'frequency'), axis_values = iml_get_frequency_axis(); else, axis_values = iml_get_range_axis(); end
        if ~isnumeric(axis_values) || numel(axis_values) ~= n, axis_values = 1:n; end
        axis_values = axis_values(:)';
        end

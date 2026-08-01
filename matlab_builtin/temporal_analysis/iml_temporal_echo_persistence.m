function result = iml_temporal_echo_persistence(varargin)
        % IML_TEMPORAL_ECHO_PERSISTENCE
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
if ~isempty(varargin) && iscell(varargin{1}), frames = varargin{1}; else, frames = iml_get_sequence(); end
        if ~iscell(frames), frames = {frames}; end
        n = numel(frames); coverage = zeros(1,n);
        for k = 1:n
          X = double(frames{k}); X(~isfinite(X)) = 0;
          if isempty(X), coverage(k) = 0; else, t = prctile(X(:),85); coverage(k) = mean(X(:) >= t); end
        end
        persistence = mean(coverage >= median(coverage));
        change = 0; if n > 1, change = mean(abs(diff(coverage))); end
        result = struct('method','iml_temporal_echo_persistence','status','candidate','frame_count',n,'coverage',coverage,'persistence',persistence,'change_rate',change);
        iml_register_feature('iml_temporal_echo_persistence_persistence',persistence,'fraction'); iml_register_candidate_result('iml_temporal_echo_persistence','candidate','Sequence heuristic; timing/profile dependent.');
        iml_add_provenance('iml_temporal_echo_persistence','v11 temporal heuristic'); if n < 2, iml_add_warning('iml_temporal_echo_persistence: sequence has fewer than two frames.'); end
        iml_save_matrix('iml_temporal_echo_persistence_coverage',coverage);
        end

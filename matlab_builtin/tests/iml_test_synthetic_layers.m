function passed = iml_test_synthetic_layers()
        % IML_TEST_SYNTHETIC_LAYERS
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
rng(11); [c,r]=meshgrid(1:80,1:60); frame=0.02*rand(size(c))+exp(-((r-20-0.2*c).^2)/8);
        candidate=iml_trace_global_threshold(frame); passed=isstruct(candidate) && isfield(candidate,'mask') && any(candidate.mask(:));
        if ~passed, error('iml_test_synthetic_layers:failed','Synthetic-only candidate test failed.'); end
        iml_add_provenance('iml_test_synthetic_layers','Synthetic-only test; not scientific validation.');
        end

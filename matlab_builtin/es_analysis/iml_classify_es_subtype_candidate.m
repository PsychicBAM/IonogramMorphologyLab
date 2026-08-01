function result = iml_classify_es_subtype_candidate(varargin)
        % IML_CLASSIFY_ES_SUBTYPE_CANDIDATE
% EN: Candidate-only, non-causal development/teaching method. Results depend on
% the selected ionogram profile, calibration, preprocessing, and thresholds.
% Limitations: this is a heuristic diagnostic aid, not a validated geophysical
% interpretation or a statement about true layer height.
% RU:  ,     /. 
%     , ,   .
% :   ,   
%        .
% Safety default: subtype labels remain disabled until an external registry explicitly activates them.
        active = false; registry_file = 'iml_es_subtype_registry.mat';
        if exist(registry_file, 'file')
          S = load(registry_file);
          if isfield(S, 'es_subtype_classifier_active'), active = logical(S.es_subtype_classifier_active); end
        end
        result = struct('method','iml_classify_es_subtype_candidate','status','unverified','label','unverified/disabled','active',active);
        if active
          result.status = 'unverified'; result.label = 'unverified/disabled';
          iml_add_warning('iml_classify_es_subtype_candidate: registry is active, but built-in v11 deliberately abstains pending validation.');
        else
          iml_add_warning('iml_classify_es_subtype_candidate: subtype classifier disabled by default; returning abstention.');
        end
        iml_register_candidate_result('iml_classify_es_subtype_candidate','unverified','Abstained: no verified Es subtype classifier.');
        iml_add_provenance('iml_classify_es_subtype_candidate','v11 safety abstention');
        end

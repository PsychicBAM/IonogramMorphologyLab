function width = iml_formula_local_width_bins(mask_1d)
% IML Phase 4A/4A.1b parity helper — HEUR_IML_TRACE_WIDTH_BINS (project heuristic)
% Requires a true 1-D vector. Does not silently flatten 2-D inputs.
    if isempty(mask_1d)
        width = NaN;
        return;
    end
    if ~isvector(mask_1d) || (~isrow(mask_1d) && ~iscolumn(mask_1d))
        width = NaN;
        return;
    end
    if ndims(mask_1d) > 2 || (ismatrix(mask_1d) && all(size(mask_1d) > 1))
        width = NaN;
        return;
    end
    bits = logical(mask_1d(:));
    if ~any(bits)
        width = 0;
        return;
    end
    padded = [false; bits; false];
    edges = diff(double(padded));
    starts = find(edges == 1);
    ends = find(edges == -1);
    width = max(ends - starts);
end

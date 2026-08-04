function out = iml_v2_branch_separation(rows_a, rows_b, cols_common)
% IML Phase 4B.2 parity — median absolute row separation on common frequency columns
    out = struct('value', NaN, 'valid', false, 'reason_invalid', '');
    if nargin < 2
        out.reason_invalid = 'insufficient_coverage';
        return;
    end
    a = double(rows_a(:));
    b = double(rows_b(:));
    if isempty(a) || isempty(b)
        out.reason_invalid = 'insufficient_coverage';
        return;
    end
    if any(~isfinite(a)) || any(~isfinite(b))
        out.reason_invalid = 'nonfinite_input';
        return;
    end
    if numel(a) ~= numel(b)
        out.reason_invalid = 'insufficient_coverage';
        return;
    end
    if nargin >= 3 && ~isempty(cols_common) && numel(cols_common) ~= numel(a)
        out.reason_invalid = 'length_mismatch';
        return;
    end
    out.value = median(abs(a - b));
    out.valid = true;
end

function out = iml_v2_local_vertical_width(profile)
% IML Phase 4B.2 parity — robust percentile local vertical width (bins)
    out = struct('value', NaN, 'valid', false, 'estimator', 'robust_percentile', 'reason_invalid', '');
    if nargin < 1 || isempty(profile)
        out.reason_invalid = 'insufficient_coverage';
        return;
    end
    p = double(profile(:));
    if any(~isfinite(p))
        out.reason_invalid = 'nonfinite_input';
        return;
    end
    p = p - median(p);
    p(p < 0) = 0;
    if sum(p) <= 0
        out.reason_invalid = 'no_peak';
        return;
    end
    cdf = cumsum(p) / sum(p);
    i_lo = find(cdf >= 0.25, 1, 'first');
    i_hi = find(cdf >= 0.75, 1, 'first');
    if isempty(i_lo) || isempty(i_hi)
        out.reason_invalid = 'fit_failed';
        return;
    end
    out.value = double(i_hi - i_lo + 1);
    out.valid = true;
end

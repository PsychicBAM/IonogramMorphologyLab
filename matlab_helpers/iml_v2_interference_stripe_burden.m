function out = iml_v2_interference_stripe_burden(interference_mask)
% IML Phase 4B.1 parity — vertical stripe burden summary
    out = struct( ...
        'stripe_count', 0, ...
        'stripe_widths_median', 0, ...
        'affected_frequency_fraction', 0, ...
        'persistence', 0, ...
        'density', 0);
    if nargin < 1 || isempty(interference_mask)
        return;
    end
    m = logical(interference_mask);
    col_frac = mean(m, 1);
    stripe = col_frac > 0.55;
    out.stripe_count = sum(stripe);
    out.affected_frequency_fraction = mean(stripe);
    out.density = mean(m(:));
    if any(stripe)
        out.persistence = mean(col_frac(stripe));
    else
        out.persistence = 0;
    end
    % Stripe widths (runs of true columns)
    widths = [];
    run = 0;
    for k = 1:numel(stripe)
        if stripe(k)
            run = run + 1;
        elseif run > 0
            widths(end+1) = run; %#ok<AGROW>
            run = 0;
        end
    end
    if run > 0
        widths(end+1) = run; %#ok<AGROW>
    end
    if ~isempty(widths)
        out.stripe_widths_median = median(widths);
    else
        out.stripe_widths_median = 0;
    end
end

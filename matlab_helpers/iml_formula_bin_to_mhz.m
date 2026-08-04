function f_mhz = iml_formula_bin_to_mhz(bin_index_0based, start_mhz, step_mhz, frequency_bins)
% IML Phase 4A/4A.1b parity helper — HEUR_BIN_TO_MHZ
% Requires an integer bin index (no silent truncation of 3.8 → 3).
    if isempty(bin_index_0based) || ~isfinite(start_mhz) || ~isfinite(step_mhz) ...
            || step_mhz <= 0 || frequency_bins <= 0
        f_mhz = NaN;
        return;
    end
    if ~isscalar(bin_index_0based) || ~isnumeric(bin_index_0based) || ~isfinite(bin_index_0based)
        f_mhz = NaN;
        return;
    end
    if abs(double(bin_index_0based) - round(double(bin_index_0based))) > 0
        f_mhz = NaN;
        return;
    end
    if islogical(bin_index_0based)
        f_mhz = NaN;
        return;
    end
    b = round(double(bin_index_0based));
    if b < 0 || b >= frequency_bins
        f_mhz = NaN;
        return;
    end
    f_mhz = double(start_mhz) + b * double(step_mhz);
end

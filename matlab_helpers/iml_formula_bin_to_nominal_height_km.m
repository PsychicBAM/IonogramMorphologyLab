function h_nom_km = iml_formula_bin_to_nominal_height_km(bin_index_0based, km_per_bin, height_bins)
% IML Phase 4A/4A.1b parity helper — HEUR_BIN_TO_NOMINAL_HEIGHT
% Nominal virtual height only — not true height (F002).
% Requires an integer bin index (no silent truncation).
    if isempty(bin_index_0based) || ~isfinite(km_per_bin) || km_per_bin <= 0 || height_bins <= 0
        h_nom_km = NaN;
        return;
    end
    if ~isscalar(bin_index_0based) || ~isnumeric(bin_index_0based) || ~isfinite(bin_index_0based)
        h_nom_km = NaN;
        return;
    end
    if islogical(bin_index_0based)
        h_nom_km = NaN;
        return;
    end
    if abs(double(bin_index_0based) - round(double(bin_index_0based))) > 0
        h_nom_km = NaN;
        return;
    end
    b = round(double(bin_index_0based));
    if b < 0 || b >= height_bins
        h_nom_km = NaN;
        return;
    end
    h_nom_km = b * double(km_per_bin);
end

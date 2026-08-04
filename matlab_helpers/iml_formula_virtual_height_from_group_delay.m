function h_prime_km = iml_formula_virtual_height_from_group_delay(tau_g_s)
% IML Phase 4A parity helper — F001
% h' = c * tau_g / 2
% Does not use Amp_all. Rejects non-finite or negative delays with NaN output.
    c_km_per_s = 299792.458;
    if isempty(tau_g_s) || ~isfinite(tau_g_s) || tau_g_s < 0
        h_prime_km = NaN;
        return;
    end
    h_prime_km = c_km_per_s * double(tau_g_s) / 2.0;
end

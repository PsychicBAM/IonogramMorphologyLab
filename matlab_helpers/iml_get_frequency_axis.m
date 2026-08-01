function ff = iml_get_frequency_axis()
S = load('iml_bridge_inputs.mat');
ff = S.iml_frequency_axis;
end

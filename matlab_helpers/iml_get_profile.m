function profile = iml_get_profile()
meta = jsondecode(fileread('iml_metadata.json'));
profile = meta.profile;
end

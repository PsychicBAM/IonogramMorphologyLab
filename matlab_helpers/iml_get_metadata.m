function meta = iml_get_metadata()
meta = jsondecode(fileread('iml_metadata.json'));
end

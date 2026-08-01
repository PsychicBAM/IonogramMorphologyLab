function iml_register_feature(feature_id, value, units)
reg = {};
if exist('iml_registered_features.json','file')
  reg = jsondecode(fileread('iml_registered_features.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
item.id = feature_id; item.value = value; item.units = units;
reg{end+1} = item;
fid = fopen('iml_registered_features.json','w');
fwrite(fid, jsonencode(reg)); fclose(fid);
end

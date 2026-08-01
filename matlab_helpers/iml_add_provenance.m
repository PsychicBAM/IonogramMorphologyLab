function iml_add_provenance(key, value)
reg = {};
if exist('iml_provenance.json','file')
  reg = jsondecode(fileread('iml_provenance.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
item.key = key; item.value = value; reg{end+1} = item;
fid = fopen('iml_provenance.json','w'); fwrite(fid, jsonencode(reg)); fclose(fid);
end

function iml_add_warning(msg)
reg = {};
if exist('iml_warnings.json','file')
  reg = jsondecode(fileread('iml_warnings.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
reg{end+1} = msg;
fid = fopen('iml_warnings.json','w'); fwrite(fid, jsonencode(reg)); fclose(fid);
end

function iml_register_candidate_result(category, status, note)
reg = {};
if exist('iml_registered_candidates.json','file')
  reg = jsondecode(fileread('iml_registered_candidates.json'));
  if ~iscell(reg), reg = num2cell(reg); end
end
item.category = category; item.status = status; item.note = note;
reg{end+1} = item;
fid = fopen('iml_registered_candidates.json','w');
fwrite(fid, jsonencode(reg)); fclose(fid);
end
